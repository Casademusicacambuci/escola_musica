import sqlite3
import csv
import io
from flask import Flask, render_template, request, redirect, url_for, Response
from datetime import datetime

app = Flask(__name__)

# Configuração e Inicialização do Banco de Dados
def init_db():
    conn = sqlite3.connect('escola.db')
    cursor = conn.cursor()
    
    # Tabela de Alunos
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS alunos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            email TEXT,
            telefone TEXT,
            instrumento TEXT,
            data_matricula TEXT
        )
    ''')
    
    # Tabela de Professores
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS professores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            email TEXT,
            telefone TEXT,
            especialidade TEXT
        )
    ''')
    
    # Tabela de Agendamentos / Locações de Estúdio
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS agendamentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tipo_agenda TEXT,
            cliente_aluno_nome TEXT,
            data TEXT,
            horario TEXT,
            horario_termino TEXT,
            valor_total REAL DEFAULT 0.0,
            status TEXT DEFAULT 'Agendado',
            observacoes TEXT
        )
    ''')
    
    # Tabela do Fluxo de Caixa / Financeiro
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS financeiro (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            origem TEXT,
            descricao TEXT,
            valor REAL NOT NULL,
            tipo_pagamento TEXT,
            data_lancamento TEXT,
            tipo TEXT NOT NULL
        )
    ''')
    
    conn.commit()
    conn.close()

# Inicializa o banco ao carregar o app
init_db()

# --- ROTA PRINCIPAL (PAINEL DE GESTÃO) ---
@app.route('/')
def index():
    conn = sqlite3.connect('escola.db')
    cursor = conn.cursor()
    
    # Buscar dados para exibição nas tabelas da interface
    cursor.execute("SELECT * FROM alunos ORDER BY id DESC")
    alunos = cursor.fetchall()
    
    cursor.execute("SELECT * FROM professores ORDER BY id DESC")
    professores = cursor.fetchall()
    
    cursor.execute("SELECT id, tipo_agenda, cliente_aluno_nome, data, horario, horario_termino, valor_total, status, observacoes FROM agendamentos ORDER BY data ASC, horario ASC")
    agendamentos = cursor.fetchall()
    
    cursor.execute("SELECT id, origem, descricao, valor, tipo_pagamento, data_lancamento, tipo FROM financeiro ORDER BY data_lancamento DESC, id DESC")
    movimentacoes = cursor.fetchall()
    
    # Calcular os totais do Painel Financeiro
    cursor.execute("SELECT SUM(valor) FROM financeiro WHERE tipo = 'ENTRADA'")
    total_entradas = cursor.fetchone()[0] or 0.0
    
    cursor.execute("SELECT SUM(valor) FROM financeiro WHERE tipo = 'SAÍDA'")
    total_saidas = cursor.fetchone()[0] or 0.0
    
    saldo_caixa = total_entradas - total_saidas
    conn.close()
    
    # saldo_atual mapeia diretamente para o index.html antigo evitando UndefinedError
    return render_template('index.html', alunos=alunos, professores=professores, 
                           agendamentos=agendamentos, movimentacoes=movimentacoes, 
                           total_entradas=total_entradas, total_saidas=total_saidas, 
                           saldo_caixa=saldo_caixa, saldo_atual=saldo_caixa)

# --- ROTAS DE CADASTRO ---
@app.route('/cadastrar_aluno', methods=['POST'])
def cadastrar_aluno():
    nome = request.form.get('nome')
    email = request.form.get('email')
    telefone = request.form.get('telefone')
    instrumento = request.form.get('instrumento')
    data_matricula = request.form.get('data_matricula') or datetime.now().strftime('%Y-%m-%d')
    
    conn = sqlite3.connect('escola.db')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO alunos (nome, email, telefone, instrumento, data_matricula) VALUES (?, ?, ?, ?, ?)",
                   (nome, email, telefone, instrumento, data_matricula))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

@app.route('/cadastrar_professor', methods=['POST'])
def cadastrar_professor():
    nome = request.form.get('nome')
    email = request.form.get('email')
    telefone = request.form.get('telefone')
    especialidade = request.form.get('especialidade')
    
    conn = sqlite3.connect('escola.db')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO professores (nome, email, telefone, especialidade) VALUES (?, ?, ?, ?, ?)",
                   (nome, email, telefone, especialidade))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

# --- ROTAS DE ESTÚDIO E LOCAÇÕES ---
@app.route('/agendar_studio', methods=['POST'])
def agendar_studio():
    tipo_agenda = request.form.get('tipo_agenda')
    cliente_aluno_nome = request.form.get('cliente_aluno_nome')
    data = request.form.get('data')
    horario = request.form.get('horario')
    horario_termino = request.form.get('horario_termino')
    valor_total = request.form.get('valor_total')
    observacoes = request.form.get('observacoes', '')
    
    valor_total = float(valor_total) if valor_total else 0.0
    
    conn = sqlite3.connect('escola.db')
    cursor = conn.cursor()
    
    # 1. Salva o agendamento
    cursor.execute('''
        INSERT INTO agendamentos (tipo_agenda, cliente_aluno_nome, data, horario, horario_termino, valor_total, status, observacoes)
        VALUES (?, ?, ?, ?, ?, ?, 'Agendado', ?)
    ''', (tipo_agenda, cliente_aluno_nome, data, horario, horario_termino, valor_total, observacoes))
    
    # 2. Lança automaticamente no Fluxo de Caixa como entrada
    descricao_financeiro = f"Locação Estúdio: {tipo_agenda.capitalize()} - {cliente_aluno_nome}"
    cursor.execute('''
        INSERT INTO financeiro (origem, descricao, valor, tipo_pagamento, data_lancamento, tipo)
        VALUES ('ESTUDIO', ?, ?, 'A definir', ?, 'ENTRADA')
    ''', (descricao_financeiro, valor_total, data))
    
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

@app.route('/atualizar_status_agendamento/<int:id>', methods=['POST'])
def atualizar_status_agendamento(id):
    novo_status = request.form.get('status')
    observacoes = request.form.get('observacoes', '')
    
    conn = sqlite3.connect('escola.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE agendamentos SET status = ?, observacoes = ? WHERE id = ?", (novo_status, observacoes, id))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

# --- ROTAS FINANCEIRAS / FLUXO MANUAL ---
@app.route('/lancar_financeiro', methods=['POST'])
def lancar_financeiro():
    tipo = request.form.get('tipo')  # ENTRADA ou SAÍDA
    origem = request.form.get('origem')
    descricao = request.form.get('descricao')
    valor = float(request.form.get('valor', 0.0))
    tipo_pagamento = request.form.get('tipo_pagamento', 'Dinheiro/Pix')
    data_lancamento = request.form.get('data_lancamento') or datetime.now().strftime('%Y-%m-%d')
    
    conn = sqlite3.connect('escola.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO financeiro (origem, descricao, valor, tipo_pagamento, data_lancamento, tipo)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (origem, descricao, valor, tipo_pagamento, data_lancamento, tipo))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

@app.route('/reverter_movimentacao/<int:id>', methods=['POST'])
def reverter_movimentacao(id):
    conn = sqlite3.connect('escola.db')
    cursor = conn.cursor()
    cursor.execute("SELECT tipo FROM financeiro WHERE id = ?", (id,))
    row = cursor.fetchone()
    if row:
        novo_tipo = 'SAÍDA' if row[0] == 'ENTRADA' else 'ENTRADA'
        cursor.execute("UPDATE financeiro SET tipo = ? WHERE id = ?", (novo_tipo, id))
        conn.commit()
    conn.close()
    return redirect(url_for('index'))

@app.route('/deletar_movimentacao/<int:id>', methods=['POST'])
def deletar_movimentacao(id):
    conn = sqlite3.connect('escola.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM financeiro WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

# --- EXPORTAÇÃO DE RELATÓRIOS EM CSV ---
@app.route('/exportar_caixa_dia', methods=['GET'])
def exportar_caixa_dia():
    data_hoje = datetime.now().strftime('%Y-%m-%d')
    conn = sqlite3.connect('escola.db')
    cursor = conn.cursor()
    cursor.execute("SELECT data_lancamento, tipo, origem, descricao, valor, tipo_pagamento FROM financeiro WHERE data_lancamento = ?", (data_hoje,))
    linhas = cursor.fetchall()
    conn.close()
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Data', 'Tipo', 'Origem', 'Descrição', 'Valor (R$)', 'Forma Pagamento'])
    for row in linhas:
        writer.writerow(row)
        
    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-disposition": f"attachment; filename=fechamento_diario_{data_hoje}.csv"}
    )

@app.route('/exportar_fechamento_mes', methods=['GET'])
def exportar_fechamento_mes():
    mes_atual = datetime.now().strftime('%Y-%m')
    conn = sqlite3.connect('escola.db')
    cursor = conn.cursor()
    cursor.execute("SELECT data_lancamento, tipo, origem, descricao, valor, tipo_pagamento FROM financeiro WHERE data_lancamento LIKE ?", (f"{mes_atual}%",))
    linhas = cursor.fetchall()
    conn.close()
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Data', 'Tipo', 'Origem', 'Descrição', 'Valor (R$)', 'Forma Pagamento'])
    for row in linhas:
        writer.writerow(row)
        
    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-disposition": f"attachment; filename=fechamento_mensal_{mes_atual}.csv"}
    )

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

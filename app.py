from flask import Flask, render_template, request, redirect, url_for, flash, Response
import sqlite3
import csv
import io
from datetime import datetime

app = Flask(__name__)
app.secret_key = "chave_secreta_cambuci"

# --- CONFIGURAÇÃO DO BANCO DE DADOS UNIFICADO ---
def init_db():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    # Tabela de Fornecedores
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS fornecedores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            cnpj TEXT,
            telefone TEXT,
            email TEXT,
            produto_servico TEXT
        )
    ''')
    
    # Tabela de Funcionários
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS funcionarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            cargo TEXT NOT NULL,
            telefone TEXT,
            email TEXT,
            salario REAL
        )
    ''')

    # Tabela de Movimentações Financeiras
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS movimentacoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data TEXT NOT NULL,
            tipo TEXT NOT NULL,
            origem TEXT,
            descricao TEXT,
            valor REAL NOT NULL
        )
    ''')

    # Tabela de Agendamentos de Estúdio
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS agendamentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tipo_agenda TEXT NOT NULL,
            cliente_aluno_nome TEXT NOT NULL,
            data TEXT NOT NULL,
            horario TEXT NOT NULL,
            horario_termino TEXT,
            valor_total REAL,
            status TEXT NOT NULL,
            observacoes TEXT
        )
    ''')
    
    conn.commit()
    conn.close()

init_db()

def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

# --- SIMULAÇÃO DE LOGIN / CONTROLE DE PERFIL ---
# Estado global simples para simular quem está logado no momento
SESSION_SIMULADA = {
    "perfil": "administrador",
    "nome_usuario": "Deni Miller"
}

@app.route('/alternar_usuario/<string:novo_perfil>')
def alternar_usuario(novo_perfil):
    if novo_perfil == 'caixa':
        SESSION_SIMULADA['perfil'] = 'operador_caixa'
        SESSION_SIMULADA['nome_usuario'] = 'Operador de Caixa'
    else:
        SESSION_SIMULADA['perfil'] = 'administrador'
        SESSION_SIMULADA['nome_usuario'] = 'Deni Miller'
    return redirect(url_for('index'))

# --- ROTA PRINCIPAL (CENTRALIZADA) ---
@app.route('/')
def index():
    conn = get_db_connection()
    perfil = SESSION_SIMULADA['perfil']
    hoje = datetime.now().strftime('%Y-%m-%d')

    # Filtro de Finanças baseado no perfil
    if perfil == 'operador_caixa':
        movimentacoes = conn.execute('SELECT * FROM movimentacoes WHERE data = ? ORDER BY id DESC', (hoje,)).fetchall()
        total_entradas = conn.execute("SELECT SUM(valor) FROM movimentacoes WHERE tipo='Entrada' AND data=?", (hoje,)).fetchone()[0] or 0.0
        total_saidas = conn.execute("SELECT SUM(valor) FROM movimentacoes WHERE tipo='Saída' AND data=?", (hoje,)).fetchone()[0] or 0.0
    else:
        movimentacoes = conn.execute('SELECT * FROM movimentacoes ORDER BY id DESC').fetchall()
        total_entradas = conn.execute("SELECT SUM(valor) FROM movimentacoes WHERE tipo='Entrada'").fetchone()[0] or 0.0
        total_saidas = conn.execute("SELECT SUM(valor) FROM movimentacoes WHERE tipo='Saída'").fetchone()[0] or 0.0

    saldo_caixa = total_entradas - total_saidas

    # Carrega dados das outras seções
    agendamentos = conn.execute('SELECT * FROM agendamentos ORDER BY data ASC, horario ASC').fetchall()
    fornecedores = conn.execute('SELECT * FROM fornecedores ORDER BY nome ASC').fetchall()
    funcionarios = conn.execute('SELECT * FROM funcionarios ORDER BY nome ASC').fetchall()
    
    conn.close()

    return render_template(
        'index.html', 
        perfil=perfil, 
        nome_usuario=SESSION_SIMULADA['nome_usuario'],
        movimentacoes=movimentacoes,
        total_entradas=total_entradas,
        total_saidas=total_saidas,
        saldo_caixa=saldo_caixa,
        agendamentos=agendamentos,
        fornecedores=fornecedores,
        funcionarios=funcionarios
    )

# --- FLUXO FINANCEIRO ---
@app.route('/lancar', methods=['POST'])
def lancar_financeiro():
    tipo = request.form['tipo']
    origem = request.form['origem']
    descricao = request.form['descricao']
    valor = float(request.form['valor'])
    data_competencia = request.form['data_competencia']
    
    if not data_competencia:
        data_competencia = datetime.now().strftime('%Y-%m-%d')

    conn = get_db_connection()
    conn.execute('''
        INSERT INTO movimentacoes (data, tipo, origem, descricao, valor)
        VALUES (?, ?, ?, ?, ?)
    ''', (data_competencia, tipo, origem, descricao, valor))
    conn.commit()
    conn.close()
    flash('Movimentação lançada com sucesso!')
    return redirect(url_for('index'))

@app.route('/excluir/<int:id>')
def excluir_financeiro(id):
    if SESSION_SIMULADA['perfil'] == 'administrador':
        conn = get_db_connection()
        conn.execute('DELETE FROM movimentacoes WHERE id = ?', (id,))
        conn.commit()
        conn.close()
        flash('Registro removido.')
    return redirect(url_for('index'))

# --- AGENDAMENTOS ESTÚDIO ---
@app.route('/agendar_studio', methods=['POST'])
def agendar_studio():
    tipo_agenda = request.form['tipo_agenda']
    cliente_aluno_nome = request.form['cliente_aluno_nome']
    data = request.form['data']
    status = request.form['status']
    horario = request.form['horario']
    horario_termino = request.form['horario_termino']
    valor_total = float(request.form['valor_total'] or 0)
    observacoes = request.form['observacoes']

    conn = get_db_connection()
    conn.execute('''
        INSERT INTO agendamentos (tipo_agenda, cliente_aluno_nome, data, horario, horario_termino, valor_total, status, observacoes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (tipo_agenda, cliente_aluno_nome, data, horario, horario_termino, valor_total, status, observacoes))
    
    # Se já foi pago, gera uma entrada automática no financeiro
    if status == 'Agendamento pago' and valor_total > 0:
        conn.execute('''
            INSERT INTO movimentacoes (data, tipo, origem, descricao, valor)
            VALUES (?, ?, ?, ?, ?)
        ''', (data, 'Entrada', 'Acessórios e Instrumentos', f"Reserva Estúdio: {cliente_aluno_nome}", valor_total))

    conn.commit()
    conn.close()
    return redirect(url_for('index'))

@app.route('/atualizar_status_studio/<int:id>', methods=['POST'])
def atualizar_status_studio(id):
    novo_status = request.form['novo_status']
    conn = get_db_connection()
    
    # Busca dados do agendamento para faturar
    agenda = conn.execute('SELECT * FROM agendamentos WHERE id = ?', (id,)).fetchone()
    if agenda:
        conn.execute('UPDATE agendamentos SET status = ? WHERE id = ?', (novo_status, id))
        if novo_status == 'Agendamento pago' and agenda['valor_total'] > 0:
            conn.execute('''
                INSERT INTO movimentacoes (data, tipo, origem, descricao, valor)
                VALUES (?, ?, ?, ?, ?)
            ''', (agenda['data'], 'Entrada', 'Acessórios e Instrumentos', f"Baixa Estúdio: {agenda['cliente_aluno_nome']}", agenda['valor_total']))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

# --- CRUD FORNECEDORES (ADMIN) ---
@app.route('/admin/fornecedor/add', methods=['POST'])
def add_fornecedor():
    nome = request.form['nome']
    cnpj = request.form['cnpj']
    telefone = request.form['telefone']
    email = request.form['email']
    produto_servico = request.form['produto_servico']
    
    conn = get_db_connection()
    conn.execute('INSERT INTO fornecedores (nome, cnpj, telefone, email, produto_servico) VALUES (?, ?, ?, ?, ?)',
                 (nome, cnpj, telefone, email, produto_servico))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

@app.route('/admin/fornecedor/delete/<int:id>')
def delete_fornecedor(id):
    conn = get_db_connection()
    conn.execute('DELETE FROM fornecedores WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

# --- CRUD FUNCIONÁRIOS (ADMIN) ---
@app.route('/admin/funcionario/add', methods=['POST'])
def add_funcionario():
    nome = request.form['nome']
    cargo = request.form['cargo']
    telefone = request.form['telefone']
    email = request.form['email']
    salario = float(request.form['salario'] or 0)
    
    conn = get_db_connection()
    conn.execute('INSERT INTO funcionarios (nome, cargo, telefone, email, salario) VALUES (?, ?, ?, ?, ?)',
                 (nome, cargo, telefone, email, salario))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

@app.route('/admin/funcionario/delete/<int:id>')
def delete_funcionario(id):
    conn = get_db_connection()
    conn.execute('DELETE FROM funcionarios WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

# --- EXPORTAÇÃO COMPLETA PARA CSV ---
@app.route('/exportar/<string:tipo>')
def exportar_csv(tipo):
    conn = get_db_connection()
    output = io.StringIO()
    writer = csv.writer(output)
    hoje = datetime.now().strftime('%Y-%m-%d')
    filename = f"{tipo}.csv"

    if tipo == 'dia':
        writer.writerow(['ID', 'Data', 'Tipo', 'Origem', 'Descrição', 'Valor'])
        rows = conn.execute('SELECT * FROM movimentacoes WHERE data = ?', (hoje,)).fetchall()
        for r in rows: writer.writerow([r['id'], r['data'], r['tipo'], r['origem'], r['descricao'], r['valor']])
    elif tipo == 'mes':
        writer.writerow(['ID', 'Data', 'Tipo', 'Origem', 'Descrição', 'Valor'])
        rows = conn.execute('SELECT * FROM movimentacoes').fetchall()
        for r in rows: writer.writerow([r['id'], r['data'], r['tipo'], r['origem'], r['descricao'], r['valor']])
    elif tipo == 'fornecedores':
         writer.writerow(['ID', 'Nome', 'CNPJ', 'Telefone', 'Email', 'Produto/Serviço'])
         rows = conn.execute('SELECT * FROM fornecedores').fetchall()
         for r in rows: writer.writerow([r['id'], r['nome'], r['cnpj'], r['telefone'], r['email'], r['produto_servico']])
    elif tipo == 'funcionarios':
         writer.writerow(['ID', 'Nome', 'Cargo', 'Telefone', 'Email', 'Salário'])
         rows = conn.execute('SELECT * FROM funcionarios').fetchall()
         for r in rows: writer.writerow([r['id'], r['nome'], r['cargo'], r['telefone'], r['email'], r['salario']])
     
    conn.close()
    output.seek(0)
    return Response(output, mimetype="text/csv", headers={"Content-disposition": f"attachment; filename={filename}"})

if __name__ == '__main__':
    app.run(debug=True)

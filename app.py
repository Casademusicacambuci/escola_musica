import os
import sqlite3
import csv
import io
from flask import Flask, render_template, request, redirect, url_for, flash, Response, session
from werkzeug.utils import secure_filename
from datetime import datetime

app = Flask(__name__)

# CONFIGURAÇÃO DE SEGURANÇA
app.secret_key = os.environ.get('SECRET_KEY', 'chave_secreta_padrao_mude_em_producao')

# Configuração de uploads para os comprovantes de endereço
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# --- CONFIGURAÇÃO DO BANCO DE DADOS (TODAS AS TABELAS UNIFICADAS) ---
def init_db():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    # 1. Tabela de Fornecedores
    cursor.execute('''CREATE TABLE IF NOT EXISTS fornecedores (
        id INTEGER PRIMARY KEY AUTOINCREMENT, 
        nome TEXT NOT NULL, 
        cnpj TEXT, 
        telefone TEXT, 
        email TEXT, 
        produto_servico TEXT
    )''')
    
    # 2. Tabela de Funcionários
    cursor.execute('''CREATE TABLE IF NOT EXISTS funcionarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT, 
        nome TEXT NOT NULL, 
        cargo TEXT NOT NULL, 
        telefone TEXT, 
        email TEXT, 
        salario REAL
    )''')
    
    # 3. Tabela de Alunos (Secretaria)
    cursor.execute('''CREATE TABLE IF NOT EXISTS alunos (
        id INTEGER PRIMARY KEY AUTOINCREMENT, 
        nome TEXT NOT NULL, 
        curso_pretendido TEXT, 
        endereco TEXT, 
        telefone TEXT, 
        email TEXT, 
        comprovante_path TEXT
    )''')
    
    # 4. Tabela de Professores (Secretaria)
    cursor.execute('''CREATE TABLE IF NOT EXISTS professores (
        id INTEGER PRIMARY KEY AUTOINCREMENT, 
        nome TEXT NOT NULL, 
        telefone TEXT, 
        email TEXT, 
        curso TEXT, 
        endereco TEXT, 
        comprovante_path TEXT
    )''')
    
    # 5. Tabela de Turmas / Vínculos de Aulas
    cursor.execute('''CREATE TABLE IF NOT EXISTS turmas_aulas (
        id INTEGER PRIMARY KEY AUTOINCREMENT, 
        aluno_id INTEGER, 
        professor_id INTEGER, 
        dia_semana TEXT, 
        horario TEXT, 
        valor_hora_aula REAL, 
        FOREIGN KEY(aluno_id) REFERENCES alunos(id), 
        FOREIGN KEY(professor_id) REFERENCES professores(id)
    )''')
    
    # 6. Tabela de Registro de Aulas Realizadas
    cursor.execute('''CREATE TABLE IF NOT EXISTS registro_aulas (
        id INTEGER PRIMARY KEY AUTOINCREMENT, 
        turma_id INTEGER, 
        data_execucao TEXT, 
        status TEXT, 
        valor_pago REAL, 
        financeiro_status TEXT, 
        FOREIGN KEY(turma_id) REFERENCES turmas_aulas(id)
    )''')
    
    # 7. Tabela de AGENDAMENTOS DOS ESTÚDIOS
    cursor.execute('''CREATE TABLE IF NOT EXISTS agendamentos_estudio (
        id INTEGER PRIMARY KEY AUTOINCREMENT, 
        cliente_nome TEXT NOT NULL, 
        tipo_servico TEXT NOT NULL, 
        data TEXT NOT NULL, 
        horario TEXT NOT NULL, 
        valor REAL DEFAULT 0.0,
        status TEXT DEFAULT 'Agendado'
    )''')
    
    # Adiciona a coluna 'valor' caso o banco de dados seja antigo e não tenha
    try:
        cursor.execute("ALTER TABLE agendamentos_estudio ADD COLUMN valor REAL DEFAULT 0.0")
    except sqlite3.OperationalError:
        pass # A coluna já existe, tudo certo!
        
    # 8. Tabela de Movimentações Financeiras Reais
    cursor.execute('''CREATE TABLE IF NOT EXISTS movimentacoes (
        id INTEGER PRIMARY KEY AUTOINCREMENT, 
        tipo TEXT, 
        origem TEXT, 
        descricao TEXT, 
        valor REAL, 
        data TEXT
    )''')
    
    conn.commit()
    conn.close()

init_db()

def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

# --- ALTERAÇÃO DE PERFIL ---
@app.route('/alternar_usuario', methods=['POST'])
def alternar_usuario():
    perfil_selecionado = request.form.get('perfil_selecionado')
    if perfil_selecionado in ['administrador', 'operador_caixa']:
        session['perfil'] = perfil_selecionado
        flash(f"Perfil alterado para {perfil_selecionado.replace('_', ' ').title()}")
    return redirect(url_for('index'))

# --- ROTA PRINCIPAL ---
@app.route('/')
def index():
    if 'perfil' not in session:
        session['perfil'] = 'administrador'
    
    perfil_atual = session['perfil']
    conn = get_db_connection()
    
    fornecedores = conn.execute('SELECT * FROM fornecedores').fetchall()
    funcionarios = conn.execute('SELECT * FROM funcionarios').fetchall()
    alunos = conn.execute('SELECT * FROM alunos').fetchall()
    professores = conn.execute('SELECT * FROM professores').fetchall()
    
    agendamentos_estudio = conn.execute('SELECT * FROM agendamentos_estudio ORDER BY data ASC, horario ASC').fetchall()
    
    turmas = conn.execute('''
        SELECT t.id, a.nome AS aluno_nome, p.nome AS professor_nome, t.dia_semana, t.horario, t.valor_hora_aula 
        FROM turmas_aulas t 
        JOIN alunos a ON t.aluno_id = a.id 
        JOIN professores p ON t.professor_id = p.id
    ''').fetchall()
    
    aulas_executadas = conn.execute('''
        SELECT r.id, a.nome AS aluno_nome, p.nome AS professor_nome, r.data_execucao, r.valor_pago, r.financeiro_status 
        FROM registro_aulas r 
        JOIN turmas_aulas t ON r.turma_id = t.id 
        JOIN alunos a ON t.aluno_id = a.id 
        JOIN professores p ON t.professor_id = p.id
    ''').fetchall()
    
    movimentacoes_orcor = conn.execute('SELECT * FROM movimentacoes ORDER BY id DESC').fetchall()
    
    total_entradas = conn.execute("SELECT SUM(valor) FROM movimentacoes WHERE tipo='Entrada'").fetchone()[0] or 0.0
    total_saidas = conn.execute("SELECT SUM(valor) FROM movimentacoes WHERE tipo='Saída'").fetchone()[0] or 0.0
    saldo_caixa = total_entradas - total_saidas
    
    conn.close()
    
    return render_template(
        'index.html', 
        fornecedores=fornecedores, 
        funcionarios=funcionarios, 
        alunos=alunos, 
        professores=professores, 
        turmas=turmas, 
        aulas_executadas=aulas_executadas, 
        agendamentos=agendamentos_estudio, 
        nome_usuario="Deni Miller", 
        perfil=perfil_atual, 
        total_entradas=total_entradas, 
        total_saidas=total_saidas, 
        saldo_caixa=saldo_caixa, 
        movimentacoes=movimentacoes_orcor
    )

# --- SEÇÃO SECRETARIA ---
@app.route('/secretaria/aluno/add', methods=['POST'])
def add_aluno():
    nome = request.form['nome']
    curso = request.form['curso_pretendido']
    endereco = request.form['endereco']
    telefone = request.form['telefone']
    email = request.form['email']
    filename = ""
    
    if 'comprovante' in request.files:
        file = request.files['comprovante']
        if file.filename != '':
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            
    conn = get_db_connection()
    conn.execute(
        "INSERT INTO alunos (nome, curso_pretendido, endereco, telefone, email, comprovante_path) VALUES (?, ?, ?, ?, ?, ?)",
        (nome, curso, endereco, telefone, email, filename)
    )
    conn.commit()
    conn.close()
    flash('Aluno matriculado com sucesso!')
    return redirect(url_for('index'))

@app.route('/secretaria/professor/add', methods=['POST'])
def add_professor():
    nome = request.form['nome']
    telefone = request.form['telefone']
    email = request.form['email']
    curso = request.form['curso']
    endereco = request.form['endereco']
    filename = ""
    
    if 'comprovante' in request.files:
        file = request.files['comprovante']
        if file.filename != '':
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            
    conn = get_db_connection()
    conn.execute(
        "INSERT INTO professores (nome, telefone, email, curso, endereco, comprovante_path) VALUES (?, ?, ?, ?, ?, ?)",
        (nome, telefone, email, curso, endereco, filename)
    )
    conn.commit()
    conn.close()
    flash('Professor cadastrado com sucesso!')
    return redirect(url_for('index'))

@app.route('/secretaria/turma/add', methods=['POST'])
def add_turma():
    aluno_id = request.form['aluno_id']
    professor_id = request.form['professor_id']
    dia_semana = request.form['dia_semana']
    horario = request.form['horario']
    valor_hora_aula = request.form['valor_hora_aula']
    
    conn = get_db_connection()
    conn.execute(
        "INSERT INTO turmas_aulas (aluno_id, professor_id, dia_semana, horario, valor_hora_aula) VALUES (?, ?, ?, ?, ?)",
        (aluno_id, professor_id, dia_semana, horario, valor_hora_aula)
    )
    conn.commit()
    conn.close()
    flash('Aula agendada na grade da Secretaria!')
    return redirect(url_for('index'))

@app.route('/professor/aula/confirmar', methods=['POST'])
def confirmar_aula():
    turma_id = request.form['turma_id']
    data_hoje = datetime.today().strftime('%Y-%m-%d %H:%M')
    
    conn = get_db_connection()
    turma = conn.execute('''
        SELECT t.*, p.nome AS prof_nome, a.nome AS aluno_nome 
        FROM turmas_aulas t 
        JOIN professores p ON t.professor_id = p.id 
        JOIN alunos a ON t.aluno_id = a.id 
        WHERE t.id = ?
    ''', (turma_id,)).fetchone()
    
    if turma:
        valor = turma['valor_hora_aula']
        desc_financeiro = f"Repasse: Aula Executada - Prof. {turma['prof_nome']} (Aluno: {turma['aluno_nome']})"
        
        conn.execute(
            "INSERT INTO registro_aulas (turma_id, data_execucao, status, valor_pago, financeiro_status) VALUES (?, ?, ?, ?, ?)",
            (turma_id, data_hoje, 'Executada', valor, 'Enviado para o Financeiro')
        )
        conn.execute(
            "INSERT INTO movimentacoes (tipo, origem, descricao, valor, data) VALUES (?, ?, ?, ?, ?)",
            ('Saída', 'Matrícula / Mensalidade', desc_financeiro, valor, data_hoje.split()[0])
        )
        conn.commit()
        flash(f"Aula confirmada! Custo de R$ {valor:.2f} repassado ao Financeiro.")
        
    conn.close()
    return redirect(url_for('index'))

@app.route('/secretaria/professor/exportar/<int:professor_id>')
def exportar_professor_csv(professor_id):
    conn = get_db_connection()
    prof = conn.execute('SELECT nome FROM professores WHERE id = ?', (professor_id,)).fetchone()
    
    if not prof:
        conn.close()
        return "Professor não encontrado", 404
        
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Extrato de Aulas - Prof. ' + prof['nome']])
    writer.writerow([])
    writer.writerow(['ID', 'Aluno', 'Data Executada', 'Valor Repasse', 'Status'])
    
    rows = conn.execute('''
        SELECT r.id, a.nome AS aluno_nome, r.data_execucao, r.valor_pago, r.financeiro_status 
        FROM registro_aulas r 
        JOIN turmas_aulas t ON r.turma_id = t.id 
        JOIN alunos a ON t.aluno_id = a.id 
        WHERE t.professor_id = ?
    ''', (professor_id,)).fetchall()
    
    total = 0.0
    for row in rows:
        writer.writerow([row['id'], row['aluno_nome'], row['data_execucao'], f"R$ {row['valor_pago']:.2f}", row['financeiro_status']])
        total += row['valor_pago']
        
    writer.writerow([])
    writer.writerow(['TOTAL A PAGAR:', f"R$ {total:.2f}"])
    
    response = Response(output.getvalue(), mimetype='text/csv')
    response.headers["Content-Disposition"] = f"attachment; filename=extrato_{secure_filename(prof['nome'])}.csv"
    conn.close()
    return response

# --- MÓDULO AGENDAS DOS ESTÚDIOS ---
@app.route('/agendar_studio', methods=['POST'])
def agendar_studio():
    cliente = request.form['cliente_nome']
    tipo = request.form['tipo_servico']
    data = request.form['data']
    horario = request.form['horario']
    valor = float(request.form.get('valor', 0.0))
    
    conn = get_db_connection()
    conflito = conn.execute(
        "SELECT * FROM agendamentos_estudio WHERE data = ? AND horario = ? AND status != 'Cancelado'", 
        (data, horario)
    ).fetchone()
    
    if conflito:
        conn.close()
        flash('⚠️ Erro: Este horário já está reservado no estúdio! Escolha outro período.')
        return redirect(url_for('index'))
        
    conn.execute(
        "INSERT INTO agendamentos_estudio (cliente_nome, tipo_servico, data, horario, valor) VALUES (?, ?, ?, ?, ?)",
        (cliente, tipo, data, horario, valor)
    )
    conn.commit()
    conn.close()
    flash('Sucesso: Horário reservado no estúdio!')
    return redirect(url_for('index'))

@app.route('/atualizar_status_studio', methods=['POST'])
def atualizar_status_studio():
    id_novo = request.form['id']
    status = request.form['status']
    data_hoje = datetime.today().strftime('%Y-%m-%d')
    
    conn = get_db_connection()
    agenda = conn.execute("SELECT * FROM agendamentos_estudio WHERE id = ?", (id_novo,)).fetchone()
    
    if agenda:
        conn.execute("UPDATE agendamentos_estudio SET status = ? WHERE id = ?", (status, id_novo))
        
        # O pulo do gato: Se marcou como "Concluído" e ainda não estava concluído antes, lança no financeiro!
        if status == 'Concluído' and agenda['status'] != 'Concluído':
            desc_financeiro = f"Estúdio: {agenda['tipo_servico']} - Cliente: {agenda['cliente_nome']}"
            valor = agenda['valor']
            conn.execute(
                "INSERT INTO movimentacoes (tipo, origem, descricao, valor, data) VALUES (?, ?, ?, ?, ?)",
                ('Entrada', 'Estúdio', desc_financeiro, valor, data_hoje)
            )
            flash(f'Serviço Concluído! R$ {valor:.2f} registrado nas Entradas do Caixa.')
        else:
            flash(f'Status do estúdio atualizado para: {status}')
            
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

# ================= FINANCEIRO E OUTROS =================
@app.route('/lancar', methods=['POST'])
def lancar():
    tipo = request.form['tipo']
    origem = request.form['origem']
    descricao = request.form['descricao']
    valor = float(request.form['valor'])
    data = request.form['data_competencia'] or datetime.today().strftime('%Y-%m-%d')
    
    conn = get_db_connection()
    conn.execute('INSERT INTO movimentacoes (tipo, origem, descricao, valor, data) VALUES (?, ?, ?, ?, ?)', (tipo, origem, descricao, valor, data))
    conn.commit()
    conn.close()
    flash('Movimentação financeira registrada!')
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)

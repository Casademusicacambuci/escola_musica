import os
import sqlite3
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "chave_secreta_cambuci_2026"
DATABASE = "cambuci.db"

UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS alunos (
            id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT NOT NULL, rg TEXT, cpf TEXT, 
            endereco TEXT, comprovante_anexo TEXT, telefone TEXT, curso TEXT, data_matricula TEXT
        )
    ''')
    cursor.execute('CREATE TABLE IF NOT EXISTS produtos (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT NOT NULL, categoria TEXT NOT NULL, preco REAL NOT NULL, estoque INTEGER NOT NULL)')
    cursor.execute('CREATE TABLE IF NOT EXISTS financeiro (id INTEGER PRIMARY KEY AUTOINCREMENT, tipo TEXT NOT NULL, categoria_fluxo TEXT NOT NULL, descricao TEXT NOT NULL, valor REAL NOT NULL, data TEXT NOT NULL)')
    cursor.execute('CREATE TABLE IF NOT EXISTS usuarios (id INTEGER PRIMARY KEY AUTOINCREMENT, usuario TEXT UNIQUE NOT NULL, senha TEXT NOT NULL, perfil TEXT NOT NULL)')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS agenda (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tipo_agendamento TEXT NOT NULL,
            nome_responsavel TEXT NOT NULL,
            rg TEXT,
            cpf TEXT,
            endereco TEXT,
            comprovante_anexo TEXT,
            telefone TEXT,
            data_compromisso TEXT NOT NULL,
            hora_inicio TEXT NOT NULL,
            hora_fim TEXT NOT NULL,
            valor_reserva REAL DEFAULT 0.0,
            status TEXT NOT NULL,
            tecnico TEXT,
            observacoes TEXT
        )
    ''')
    
    cursor.execute("INSERT OR IGNORE INTO usuarios (usuario, senha, perfil) VALUES ('admin', 'admin123', 'administrador')")
    cursor.execute("INSERT OR IGNORE INTO usuarios (usuario, senha, perfil) VALUES ('caixa', 'caixa123', 'caixa')")
    cursor.execute("INSERT OR IGNORE INTO usuarios (usuario, senha, perfil) VALUES ('secretaria', 'sec123', 'secretaria')")
    
    conn.commit()
    conn.close()

init_db()

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        usuario = request.form.get('usuario')
        senha = request.form.get('senha')
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM usuarios WHERE usuario = ? AND senha = ?', (usuario, senha)).fetchone()
        conn.close()
        if user:
            session['logged_in'] = True
            session['usuario'] = user['usuario']
            session['perfil'] = user['perfil']
            return redirect(url_for('index'))
        else:
            flash('Usuário ou senha incorretos!', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/')
def index():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    alunos = conn.execute('SELECT * FROM alunos').fetchall()
    produtos = conn.execute('SELECT * FROM produtos').fetchall()
    movimentacoes = conn.execute('SELECT * FROM financeiro ORDER BY id DESC').fetchall()
    
    # Busca os compromissos ordenados cronologicamente por Data e Hora de início
    compromissos_raw = conn.execute('SELECT * FROM agenda ORDER BY data_compromisso ASC, hora_inicio ASC').fetchall()
    
    total_entradas = conn.execute("SELECT SUM(valor) FROM financeiro WHERE tipo='entrada'").fetchone()[0] or 0.0
    total_saidas = conn.execute("SELECT SUM(valor) FROM financeiro WHERE tipo='saida'").fetchone()[0] or 0.0
    saldo_caixa = total_entradas - total_saidas
    conn.close()
    
    # Mapeamento de meses em português para o cabeçalho visual
    meses_pt = {
        "01": "Janeiro", "02": "Fevereiro", "03": "Março", "04": "Abril",
        "05": "Maio", "06": "Junho", "07": "Julho", "08": "Agosto",
        "09": "Setembro", "10": "Outubro", "11": "Novembro", "12": "Dezembro"
    }
    
    # Agrupando os compromissos por Mês e Dia dinamicamente para o template HTML
    compromissos_agrupados = {}
    for comp in compromissos_raw:
        try:
            dt = datetime.strptime(comp['data_compromisso'], '%Y-%m-%d')
            ano_mes = dt.strftime('%Y-%m')
            nome_mes = f"{meses_pt.get(dt.strftime('%m'), 'Mês')} / {dt.strftime('%Y')}"
            dia_formatado = dt.strftime('%d/%m (%a)').replace('Mon', 'Seg').replace('Tue', 'Ter').replace('Wed', 'Qua').replace('Thu', 'Qui').replace('Fri', 'Sex').replace('Sat', 'Sáb').replace('Sun', 'Dom')
        except:
            ano_mes = "Sem Data"
            nome_mes = "Agendamentos Sem Data Definida"
            dia_formatado = comp['data_compromisso']
            
        if nome_mes not in compromissos_agrupados:
            compromissos_agrupados[nome_mes] = {}
        if dia_formatado not in compromissos_agrupados[nome_mes]:
            compromissos_agrupados[nome_mes][dia_formatado] = []
            
        compromissos_agrupados[nome_mes][dia_formatado].append(comp)
    
    return render_template('index.html', alunos=alunos, produtos=produtos, movimentacoes=movimentacoes, 
                           compromissos_agrupados=compromissos_agrupados, compromissos_raw=compromissos_raw,
                           total_entradas=total_entradas, total_saidas=total_saidas, saldo_caixa=saldo_caixa)

@app.route('/agendar', methods=['POST'])
def agendar():
    tipo = request.form.get('tipo_agendamento')
    nome = request.form.get('nome_responsavel')
    rg = request.form.get('rg')
    cpf = request.form.get('cpf')
    endereco = request.form.get('endereco')
    telefone = request.form.get('telefone')
    data_compromisso = request.form.get('data_compromisso')
    hora_inicio = request.form.get('hora_inicio')
    hora_fim = request.form.get('hora_fim')
    valor_reserva = float(request.form.get('valor_reserva') or 0.0)
    status = request.form.get('status')
    tecnico = request.form.get('tecnico') or "Não designado"
    observacoes = request.form.get('observacoes')
    
    conn = get_db_connection()
    
    conflito = conn.execute('''
        SELECT * FROM agenda 
        WHERE tipo_agendamento = ? 
        AND data_compromisso = ? 
        AND NOT (hora_fim <= ? OR hora_inicio >= ?)
    ''', (tipo, data_compromisso, hora_inicio, hora_fim)).fetchone()
    
    if conflito:
        conn.close()
        flash(f'ALERTA: O {tipo} já está ocupado neste dia entre {conflito["hora_inicio"]} e {conflito["hora_fim"]}!', 'danger')
        return redirect(url_for('index'))
    
    filename = ""
    file = request.files.get('comprovante')
    if file and allowed_file(file.filename):
        filename = secure_filename(f"agenda_{cpf if cpf else 'cliente'}_{file.filename}")
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

    conn.execute('''
        INSERT INTO agenda (tipo_agendamento, nome_responsavel, rg, cpf, endereco, comprovante_anexo, telefone, data_compromisso, hora_inicio, hora_fim, valor_reserva, status, tecnico, observacoes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (tipo, nome, rg, cpf, endereco, filename, telefone, data_compromisso, hora_inicio, hora_fim, valor_reserva, status, tecnico, observacoes))
    
    if status == 'Pago' and valor_reserva > 0:
        # Envia descrição rica no primeiro cadastro caso venha como Pago
        descricao_financeiro = f"Reserva {tipo} | Cli: {nome} | Téc: {tecnico} | Data: {data_compromisso} ({hora_inicio}-{hora_fim})"
        conn.execute('''
            INSERT INTO financeiro (tipo, categoria_fluxo, descricao, valor, data)
            VALUES (?, ?, ?, ?, ?)
        ''', ('entrada', 'Estúdios', descricao_financeiro, valor_reserva, datetime.now().strftime('%Y-%m-%d %H:%M')))

    conn.commit()
    conn.close()
    flash('Agendamento fixado com sucesso!', 'success')
    return redirect(url_for('index'))

@app.route('/editar_agenda', methods=['POST'])
def editar_agenda():
    agenda_id = request.form.get('id')
    tipo = request.form.get('tipo_agendamento')
    nome = request.form.get('nome_responsavel')
    tecnico = request.form.get('tecnico')
    data_compromisso = request.form.get('data_compromisso')
    hora_inicio = request.form.get('hora_inicio')
    hora_fim = request.form.get('hora_fim')
    valor_reserva = float(request.form.get('valor_reserva') or 0.0)
    observacoes = request.form.get('observacoes')
    
    conn = get_db_connection()
    
    conflito = conn.execute('''
        SELECT * FROM agenda 
        WHERE tipo_agendamento = ? 
        AND data_compromisso = ? 
        AND id != ?
        AND NOT (hora_fim <= ? OR hora_inicio >= ?)
    ''', (tipo, data_compromisso, agenda_id, hora_inicio, hora_fim)).fetchone()
    
    if conflito:
        conn.close()
        flash(f'Erro na Edição: {tipo} já ocupado das {conflito["hora_inicio"]} às {conflito["hora_fim"]}!', 'danger')
        return redirect(url_for('index'))
        
    conn.execute('''
        UPDATE agenda SET tipo_agendamento=?, nome_responsavel=?, tecnico=?, data_compromisso=?, hora_inicio=?, hora_fim=?, valor_reserva=?, observacoes=?
        WHERE id=?
    ''', (tipo, nome, tecnico, data_compromisso, hora_inicio, hora_fim, valor_reserva, observacoes, agenda_id))
    conn.commit()
    conn.close()
    flash('Agendamento atualizado com sucesso!', 'success')
    return redirect(url_for('index'))

@app.route('/atualizar_status_agenda/<int:id>/<string:novo_status>')
def atualizar_status_agenda(id, novo_status):
    conn = get_db_connection()
    compromisso = conn.execute('SELECT * FROM agenda WHERE id = ?', (id,)).fetchone()
    
    if compromisso:
        status_anterior = compromisso['status']
        if novo_status in ['Pago', 'Concluído'] and status_anterior == 'A pagar' and compromisso['valor_reserva'] > 0:
            # INCLUSÃO COMPLETA DE DADOS ENVIADOS AO FINANCEIRO (Incluso o Técnico)
            descricao_financeiro = f"Pgto Recebido ({novo_status}) - {compromisso['tipo_agendamento']} | Cli: {compromisso['nome_responsavel']} | Téc: {compromisso['tecnico']} | Data: {compromisso['data_compromisso']}"
            conn.execute('''
                INSERT INTO financeiro (tipo, categoria_fluxo, descricao, valor, data)
                VALUES (?, ?, ?, ?, ?)
            ''', ('entrada', 'Estúdios', descricao_financeiro, compromisso['valor_reserva'], datetime.now().strftime('%Y-%m-%d %H:%M')))
            
        conn.execute('UPDATE agenda SET status = ? WHERE id = ?', (novo_status, id))
        conn.commit()
        
    conn.close()
    return redirect(url_for('index'))

@app.route('/cadastrar_aluno', methods=['POST'])
def cadastrar_aluno():
    nome, rg, cpf, endereco, telefone, curso = request.form.get('nome'), request.form.get('rg'), request.form.get('cpf'), request.form.get('endereco'), request.form.get('telefone'), request.form.get('curso')
    filename = ""
    file = request.files.get('comprovante')
    if file and allowed_file(file.filename):
        filename = secure_filename(f"aluno_{cpf}_{file.filename}")
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
    conn = get_db_connection()
    conn.execute('INSERT INTO alunos (nome, rg, cpf, endereco, comprovante_anexo, telefone, curso, data_matricula) VALUES (?, ?, ?, ?, ?, ?, ?, ?)', (nome, rg, cpf, endereco, filename, telefone, curso, datetime.now().strftime('%Y-%m-%d')))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)

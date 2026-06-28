import os
import sqlite3
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.utils import secure_filename

app = Flask(__name__)
# Chave secreta para gerenciar sessões e mensagens flash
app.secret_key = "chave_secreta_cambuci_2026"
DATABASE = "cambuci.db"

# Configuração para upload de arquivos
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# --- FUNÇÕES AUXILIARES ---

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# --- INICIALIZAÇÃO DO BANCO DE DADOS ---

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Tabela de Alunos
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS alunos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            rg TEXT,
            cpf TEXT,
            endereco TEXT,
            comprovante_anexo TEXT,
            telefone TEXT,
            curso TEXT,
            data_matricula TEXT
        )
    ''')
    
    # Tabela de Produtos (Estoque)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS produtos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            categoria TEXT NOT NULL,
            preco REAL NOT NULL,
            estoque INTEGER NOT NULL
        )
    ''')
    
    # Tabela do Financeiro (Fluxo de Caixa)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS financeiro (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tipo TEXT NOT NULL,          # 'entrada' ou 'saida'
            categoria_fluxo TEXT NOT NULL, # 'Matrículas', 'Estúdios', etc.
            descricao TEXT NOT NULL,    # A descrição "rica" que corrigimos
            valor REAL NOT NULL,
            data TEXT NOT NULL          # Data e Hora do lançamento
        )
    ''')
    
    # Tabela de Usuários (Acesso)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario TEXT UNIQUE NOT NULL,
            senha TEXT NOT NULL,
            perfil TEXT NOT NULL
        )
    ''')
    
    # Tabela da Agenda (Estúdios)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS agenda (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tipo_agendamento TEXT NOT NULL, # 'Reserva Estúdio' ou 'Locação de Equipamentos'
            nome_responsavel TEXT NOT NULL,
            rg TEXT,
            cpf TEXT,
            endereco TEXT,
            comprovante_anexo TEXT,
            telefone TEXT,
            data_compromisso TEXT NOT NULL, # Formato YYYY-MM-DD
            hora_inicio TEXT NOT NULL,
            hora_fim TEXT NOT NULL,
            valor_reserva REAL DEFAULT 0.0,
            status TEXT NOT NULL,          # 'A pagar', 'Pago', 'Concluído'
            tecnico TEXT,                  # Técnico de áudio
            observacoes TEXT
        )
    ''')
    
    # Cria usuários padrão se não existirem
    cursor.execute("INSERT OR IGNORE INTO usuarios (usuario, senha, perfil) VALUES ('admin', 'admin123', 'administrador')")
    cursor.execute("INSERT OR IGNORE INTO usuarios (usuario, senha, perfil) VALUES ('caixa', 'caixa123', 'caixa')")
    cursor.execute("INSERT OR IGNORE INTO usuarios (usuario, senha, perfil) VALUES ('secretaria', 'sec123', 'secretaria')")
    
    conn.commit()
    conn.close()

# Inicializa o banco ao rodar o app
init_db()

# --- ROTAS DE ACESSO (LOGIN/LOGOUT) ---

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

# --- ROTA PRINCIPAL (INDEX) ---

@app.route('/')
def index():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    
    # Coleta dados para os cards
    alunos = conn.execute('SELECT * FROM alunos').fetchall()
    produtos = conn.execute('SELECT * FROM produtos').fetchall()
    movimentacoes = conn.execute('SELECT * FROM financeiro ORDER BY id DESC').fetchall()
    
    # Coleta dados brutos da agenda
    compromissos_raw = conn.execute('SELECT * FROM agenda ORDER BY data_compromisso ASC, hora_inicio ASC').fetchall()
    
    # Cálculos Financeiros
    total_entradas = conn.execute("SELECT SUM(valor) FROM financeiro WHERE tipo='entrada'").fetchone()[0] or 0.0
    total_saidas = conn.execute("SELECT SUM(valor) FROM financeiro WHERE tipo='saida'").fetchone()[0] or 0.0
    saldo_caixa = total_entradas - total_saidas
    conn.close()
    
    # Estruturação da Agenda (Mês/Dia)
    meses_pt = {
        "01": "Janeiro", "02": "Fevereiro", "03": "Março", "04": "Abril",
        "05": "Maio", "06": "Junho", "07": "Julho", "08": "Agosto",
        "09": "Setembro", "10": "Outubro", "11": "Novembro", "12": "Dezembro"
    }
    
    compromissos_agrupados = {}
    for comp in compromissos_raw:
        try:
            dt = datetime.strptime(comp['data_compromisso'], '%Y-%m-%d')
            nome_mes = f"{meses_pt.get(dt.strftime('%m'), 'Mês')} / {dt.strftime('%Y')}"
            dia_formatado = dt.strftime('%d/%m (%a)').replace('Mon', 'Seg').replace('Tue', 'Ter').replace('Wed', 'Qua').replace('Thu', 'Qui').replace('Fri', 'Sex').replace('Sat', 'Sáb').replace('Sun', 'Dom')
        except:
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

# --- ROTAS DA SECRETARIA (ALUNOS) ---

@app.route('/cadastrar_aluno', methods=['POST'])
def cadastrar_aluno():
    nome = request.form.get('nome')
    rg = request.form.get('rg')
    cpf = request.form.get('cpf')
    endereco = request.form.get('endereco')
    telefone = request.form.get('telefone')
    curso = request.form.get('curso')
    
    # Upload do comprovante
    filename = ""
    file = request.files.get('comprovante')
    if file and allowed_file(file.filename):
        filename = secure_filename(f"aluno_{cpf}_{file.filename}")
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        
    conn = get_db_connection()
    conn.execute('INSERT INTO alunos (nome, rg, cpf, endereco, comprovante_anexo, telefone, curso, data_matricula) VALUES (?, ?, ?, ?, ?, ?, ?, ?)', (nome, rg, cpf, endereco, filename, telefone, curso, datetime.now().strftime('%Y-%m-%d')))
    conn.commit()
    conn.close()
    flash('Aluno cadastrado com sucesso!', 'success')
    return redirect(url_for('index'))

# --- ROTAS DA AGENDA E FINANCEIRO (ESTÚDIOS) ---

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
    
    # Verifica conflitos de horário
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
    
    # Upload do comprovante
    filename = ""
    file = request.files.get('comprovante')
    if file and allowed_file(file.filename):
        filename = secure_filename(f"agenda_{cpf if cpf else 'cliente'}_{file.filename}")
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

    # Insere na agenda
    conn.execute('''
        INSERT INTO agenda (tipo_agendamento, nome_responsavel, rg, cpf, endereco, comprovante_anexo, telefone, data_compromisso, hora_inicio, hora_fim, valor_reserva, status, tecnico, observacoes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (tipo, nome, rg, cpf, endereco, filename, telefone, data_compromisso, hora_inicio, hora_fim, valor_reserva, status, tecnico, observacoes))
    
    # Se o agendamento já foi criado como 'Pago', lança no financeiro IMEDIATAMENTE
    if status == 'Pago' and valor_reserva > 0:
        # Monta a descrição rica e detalhada
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
    
    # Verifica conflitos de horário (ignorando o agendamento atual)
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

# --- A FUNÇÃO QUE CORRIGIMOS ---

@app.route('/atualizar_status_agenda/<int:id>/<string:novo_status>')
def atualizar_status_agenda(id, novo_status):
    """
    Função corrigida para garantir que, ao clicar em 'Concluir' ou 'Pago',
    todos os detalhes (Cliente, Técnico, Espaço, Data, Horários) sejam
    enviados perfeitamente para o financeiro.
    """
    conn = get_db_connection()
    
    # Pesquisa os detalhes da reserva pelo ID
    compromisso = conn.execute('SELECT * FROM agenda WHERE id = ?', (id,)).fetchone()
    
    if compromisso:
        status_anterior = compromisso['status']
        valor = compromisso['valor_reserva']
        
        # Lógica para processar o pagamento no financeiro.
        # Condição: Mudar de 'A pagar' para um status pago ('Pago' ou 'Concluído') e ter valor > 0.
        if novo_status in ['Pago', 'Concluído'] and status_anterior == 'A pagar' and valor > 0:
            
            # --- COLETA DE DADOS RICOS DO AGENDAMENTO ---
            # Garante um valor padrão para o técnico para evitar erros de NoneType.
            tecnico_nome = compromisso['tecnico'] if compromisso['tecnico'] else "Não designado"
            cliente_nome = compromisso['nome_responsavel']
            tipo_espaco = compromisso['tipo_agendamento']
            data_compromisso = compromisso['data_compromisso']
            # Formata os horários para ficarem limpos (ex: 15:00-17:00)
            horarios = f"{compromisso['hora_inicio']}-{compromisso['hora_fim']}"
            
            # --- MONTAGEM DA DESCRIÇÃO RICA E DETALHADA ---
            # Esta linha cria a descrição exatamente como você validou no protótipo visual.
            descricao_financeiro = f"Faturamento ({novo_status}) - {tipo_espaco} | Cli: {cliente_nome} | Téc: {tecnico_nome} | Data: {data_compromisso} ({horarios})"
            
            # --- LANÇAMENTO NO FLUXO DE CAIXA (Tabela financeiro) ---
            conn.execute('''
                INSERT INTO financeiro (tipo, categoria_fluxo, descricao, valor, data)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                'entrada',                                      # Tipo: Entrada de dinheiro
                'Estúdios',                                     # Categoria para relatórios
                descricao_financeiro,                          # Descrição completa e detalhada
                valor,                                          # Valor da reserva
                datetime.now().strftime('%Y-%m-%d %H:%M')      # Data/Hora do lançamento
            ))
            
        # --- ATUALIZAÇÃO DO STATUS NA TABELA DA AGENDA ---
        conn.execute('UPDATE agenda SET status = ? WHERE id = ?', (novo_status, id))
        conn.commit()
        
    conn.close()
    flash(f'Agendamento {id} atualizado para {novo_status} com sucesso e financeiro processado.', 'success')
    return redirect(url_for('index'))

# --- FIM DO ARQUIVO ---

if __name__ == '__main__':
    app.run(debug=True)

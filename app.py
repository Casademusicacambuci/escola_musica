from flask import Flask, render_template, request, redirect, url_for, flash, session, Response
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os
import csv
from io import StringIO

from models import db, Usuario, Aluno, Professor

app = Flask(__name__)
app.secret_key = 'chave_secreta_cambuci_2026' 
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///cambuci_crm.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

db.init_app(app)

with app.app_context():
    db.create_all() 
    
    admin_existente = Usuario.query.filter_by(username='admin').first()
    if not admin_existente:
        senha_criptografada = generate_password_hash('admin123')
        novo_admin = Usuario(
            username='admin', password_hash=senha_criptografada,
            nome_completo='Administrador Geral', role='admin'
        )
        db.session.add(novo_admin)
        db.session.commit()

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        usuario = Usuario.query.filter_by(username=username).first()
        
        if usuario and check_password_hash(usuario.password_hash, password):
            session['usuario_id'] = usuario.id
            session['role'] = usuario.role
            session['nome'] = usuario.nome_completo
            return redirect(url_for('dashboard'))
        else:
            flash('Usuário ou senha incorretos.')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/')
def index():
    if 'usuario_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    return render_template('dashboard.html', nome=session.get('nome'), role=session.get('role'))

# --- MÓDULO SECRETARIA: ALUNOS ---
@app.route('/secretaria/alunos', methods=['GET', 'POST'])
def gerenciar_alunos():
    if 'usuario_id' not in session or session.get('role') not in ['admin', 'secretaria']:
        flash('Acesso negado.')
        return redirect(url_for('dashboard'))
        
    if request.method == 'POST':
        # Tratamento de datas
        data_nasc_str = request.form.get('data_nascimento')
        data_mat_str = request.form.get('data_matricula')
        
        data_nasc = datetime.strptime(data_nasc_str, '%Y-%m-%d').date() if data_nasc_str else None
        data_mat = datetime.strptime(data_mat_str, '%Y-%m-%d').date() if data_mat_str else datetime.utcnow().date()

        cpf = request.form.get('cpf')
        arquivo = request.files.get('comprovante')
        caminho_arquivo = None
        if arquivo and arquivo.filename != '':
            extensao = arquivo.filename.split('.')[-1]
            nome_arquivo = f"comprovante_{cpf}.{extensao}"
            arquivo.save(os.path.join(app.config['UPLOAD_FOLDER'], nome_arquivo))
            caminho_arquivo = f"uploads/{nome_arquivo}"

        aluno_existente = Aluno.query.filter_by(cpf=cpf).first()
        if aluno_existente:
            flash('Erro: CPF já cadastrado.')
        else:
            novo_aluno = Aluno(
                nome=request.form.get('nome'),
                cpf=cpf,
                email=request.form.get('email'),
                data_nascimento=data_nasc,
                nome_responsavel=request.form.get('responsavel'),
                endereco_completo=request.form.get('endereco'),
                comprovante_endereco=caminho_arquivo,
                telefone=request.form.get('telefone'),
                curso=request.form.get('curso'),
                nivel=request.form.get('nivel'),
                data_matricula=data_mat,
                status=request.form.get('status')
            )
            db.session.add(novo_aluno)
            db.session.commit()
            flash('Aluno matriculado com sucesso!')
            return redirect(url_for('gerenciar_alunos'))

    todos_alunos = Aluno.query.order_by(Aluno.nome).all()
    return render_template('alunos.html', alunos=todos_alunos)

# --- MÓDULO SECRETARIA: EXPORTAR CSV (ATUALIZADO) ---
@app.route('/secretaria/alunos/csv')
def exportar_alunos_csv():
    if 'usuario_id' not in session or session.get('role') not in ['admin', 'secretaria']:
        return redirect(url_for('dashboard'))
        
    alunos = Aluno.query.all()
    
    si = StringIO()
    cw = csv.writer(si, delimiter=';') 
    
    # Adicionamos todas as colunas que você pediu aqui no cabeçalho
    cw.writerow(['Nome', 'CPF', 'Data de Nascimento', 'Email', 'Telefone', 'Responsável', 'Endereço Completo', 'Curso', 'Nível', 'Status', 'Data da Matrícula'])
    
    for a in alunos:
        # Formatando as datas para o padrão brasileiro (DD/MM/AAAA)
        data_nasc_formatada = a.data_nascimento.strftime('%d/%m/%Y') if a.data_nascimento else ''
        data_mat_formatada = a.data_matricula.strftime('%d/%m/%Y') if a.data_matricula else ''
        
        # Inserindo os dados de cada aluno na planilha, na mesma ordem do cabeçalho
        cw.writerow([
            a.nome, 
            a.cpf, 
            data_nasc_formatada, 
            a.email, 
            a.telefone, 
            a.nome_responsavel,
            a.endereco_completo,
            a.curso, 
            a.nivel, 
            a.status, 
            data_mat_formatada
        ])
        
    output = si.getvalue()
    # Retorna o CSV com codificação UTF-8 BOM para garantir acentos corretos no Excel
    return Response(
        '\ufeff' + output, 
        mimetype="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment;filename=relatorio_completo_alunos.csv"}
    )

# --- MÓDULO SECRETARIA: PROFESSORES ---
@app.route('/secretaria/professores', methods=['GET', 'POST'])
def gerenciar_professores():
    if 'usuario_id' not in session or session.get('role') not in ['admin', 'secretaria']:
        flash('Acesso negado.')
        return redirect(url_for('dashboard'))
        
    if request.method == 'POST':
        cpf = request.form.get('cpf')
        arquivo = request.files.get('comprovante')
        caminho_arquivo = None
        if arquivo and arquivo.filename != '':
            extensao = arquivo.filename.split('.')[-1]
            nome_arquivo = f"comprovante_prof_{cpf}.{extensao}"
            arquivo.save(os.path.join(app.config['UPLOAD_FOLDER'], nome_arquivo))
            caminho_arquivo = f"uploads/{nome_arquivo}"

        prof_existente = Professor.query.filter_by(cpf=cpf).first()
        if prof_existente:
            flash('Erro: CPF já cadastrado.')
        else:
            novo_prof = Professor(
                nome=request.form.get('nome'),
                cpf=cpf,
                email=request.form.get('email'),
                endereco_completo=request.form.get('endereco'),
                comprovante_endereco=caminho_arquivo,
                telefone=request.form.get('telefone'),
                curso=request.form.get('curso'),
                status=request.form.get('status')
            )
            db.session.add(novo_prof)
            db.session.commit()
            flash('Professor cadastrado com sucesso!')
            return redirect(url_for('gerenciar_professores'))

    todos_professores = Professor.query.order_by(Professor.nome).all()
    return render_template('professores.html', professores=todos_professores)

if __name__ == '__main__':
    app.run(debug=True)

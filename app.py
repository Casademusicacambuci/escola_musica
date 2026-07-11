from flask import Flask, render_template, request, redirect, url_for, flash, session, Response
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os
import csv
from io import StringIO

from models import db, Usuario, Aluno, Professor, AgendamentoEstudio

app = Flask(__name__)
app.secret_key = 'chave_secreta_cambuci_2026' 
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///cambuci_crm.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

db.init_app(app)

with app.app_context():
    AgendamentoEstudio.__table__.drop(db.engine, checkfirst=True)
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
        usuario = Usuario.query.filter_by(username=request.form.get('username')).first()
        if usuario and check_password_hash(usuario.password_hash, request.form.get('password')):
            session['usuario_id'] = usuario.id
            session['role'] = usuario.role
            session['nome'] = usuario.nome_completo
            return redirect(url_for('dashboard'))
        flash('Usuário ou senha incorretos.')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/')
def index():
    return redirect(url_for('dashboard')) if 'usuario_id' in session else redirect(url_for('login'))

@app.route('/dashboard')
def dashboard():
    if 'usuario_id' not in session: return redirect(url_for('login'))
    return render_template('dashboard.html', nome=session.get('nome'), role=session.get('role'))

# --- MÓDULO SECRETARIA (Alunos e Professores - Resumido para caber) ---
@app.route('/secretaria/alunos', methods=['GET', 'POST'])
def gerenciar_alunos():
    if 'usuario_id' not in session: return redirect(url_for('login'))
    todos_alunos = Aluno.query.order_by(Aluno.nome).all()
    return render_template('alunos.html', alunos=todos_alunos)

@app.route('/secretaria/professores', methods=['GET', 'POST'])
def gerenciar_professores():
    if 'usuario_id' not in session: return redirect(url_for('login'))
    todos_professores = Professor.query.order_by(Professor.nome).all()
    return render_template('professores.html', professores=todos_professores)

# ==============================================================================
# MÓDULOS 03, 04 E 05 - ESTÚDIOS (GRAVAÇÃO, VIDEOCLIPE E ENSAIO)
# ==============================================================================
@app.route('/estudios', methods=['GET', 'POST'])
def gerenciar_estudios():
    if 'usuario_id' not in session or session.get('role') not in ['admin', 'estudio', 'secretaria']:
        flash('Acesso negado aos estúdios.')
        return redirect(url_for('dashboard'))
        
    if request.method == 'POST':
        # Conversão de Datas e Horários
        data_str = request.form.get('data_agendamento')
        hora_inicio_str = request.form.get('horario_inicio')
        hora_fim_str = request.form.get('horario_final')
        
        data_agendamento = datetime.strptime(data_str, '%Y-%m-%d').date() if data_str else datetime.utcnow().date()
        horario_inicio = datetime.strptime(hora_inicio_str, '%H:%M').time()
        horario_final = datetime.strptime(hora_fim_str, '%H:%M').time()

        cpf = request.form.get('cpf')
        arquivo = request.files.get('comprovante')
        caminho_arquivo = None
        if arquivo and arquivo.filename != '':
            extensao = arquivo.filename.split('.')[-1]
            nome_arquivo = f"comprovante_estudio_{cpf}_{data_str}.{extensao}"
            arquivo.save(os.path.join(app.config['UPLOAD_FOLDER'], nome_arquivo))
            caminho_arquivo = f"uploads/{nome_arquivo}"

        novo_agendamento = AgendamentoEstudio(
            tipo_estudio=request.form.get('tipo_estudio'),
            nome_cliente=request.form.get('nome_cliente'),
            cpf=cpf, telefone=request.form.get('telefone'),
            endereco_completo=request.form.get('endereco'),
            comprovante_endereco=caminho_arquivo,
            data_agendamento=data_agendamento,
            horario_inicio=horario_inicio, horario_final=horario_final,
            nome_tecnico=request.form.get('nome_tecnico'),
            status_pagamento=request.form.get('status_pagamento'),
            status_trabalho=request.form.get('status_trabalho'),
            observacoes=request.form.get('observacoes')
        )
        db.session.add(novo_agendamento)
        db.session.commit()
        flash('Agendamento de estúdio criado com sucesso!')
        return redirect(url_for('gerenciar_estudios'))

    agendamentos = AgendamentoEstudio.query.order_by(AgendamentoEstudio.data_agendamento.desc()).all()
    return render_template('estudios.html', agendamentos=agendamentos)

@app.route('/estudios/editar/<int:id>', methods=['POST'])
def editar_estudio(id):
    if 'usuario_id' not in session: return redirect(url_for('login'))
    
    ag = AgendamentoEstudio.query.get_or_404(id)
    ag.status_pagamento = request.form.get('status_pagamento')
    ag.status_trabalho = request.form.get('status_trabalho')
    ag.nome_tecnico = request.form.get('nome_tecnico')
    ag.observacoes = request.form.get('observacoes')
    
    # Se o trabalho foi concluído, deixamos a informação pronta para o Financeiro puxar depois!
    db.session.commit()
    flash('Status do agendamento atualizado!')
    return redirect(url_for('gerenciar_estudios'))

@app.route('/estudios/excluir/<int:id>', methods=['POST'])
def excluir_estudio(id):
    if 'usuario_id' not in session: return redirect(url_for('login'))
    ag = AgendamentoEstudio.query.get_or_404(id)
    db.session.delete(ag)
    db.session.commit()
    flash('Agendamento cancelado/excluído.')
    return redirect(url_for('gerenciar_estudios'))

if __name__ == '__main__':
    app.run(debug=True)

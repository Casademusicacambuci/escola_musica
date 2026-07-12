from flask import Flask, render_template, request, redirect, url_for, flash, session, Response, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os
import csv
from io import StringIO

from models import db, Usuario, Aluno, Professor, AgendamentoEstudio, Aula

app = Flask(__name__)
app.secret_key = 'chave_secreta_cambuci_2026' 
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///cambuci_crm.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

db.init_app(app)

with app.app_context():
    # Recria APENAS a tabela de aulas para as novas colunas
    Aula.__table__.drop(db.engine, checkfirst=True)
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

# ==============================================================================
# SECRETARIA: ALUNOS E PROFESSORES
# ==============================================================================
@app.route('/secretaria/alunos', methods=['GET', 'POST'])
def gerenciar_alunos():
    if 'usuario_id' not in session: return redirect(url_for('login'))
    if request.method == 'POST':
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

        if Aluno.query.filter_by(cpf=cpf).first():
            flash('Erro: CPF já cadastrado.')
        else:
            novo_aluno = Aluno(nome=request.form.get('nome'), cpf=cpf, email=request.form.get('email'),
                               data_nascimento=data_nasc, nome_responsavel=request.form.get('responsavel'),
                               endereco_completo=request.form.get('endereco'), comprovante_endereco=caminho_arquivo,
                               telefone=request.form.get('telefone'), curso=request.form.get('curso'),
                               nivel=request.form.get('nivel'), data_matricula=data_mat, status=request.form.get('status'))
            db.session.add(novo_aluno)
            db.session.commit()
            flash('Aluno matriculado com sucesso!')
            return redirect(url_for('gerenciar_alunos'))
    return render_template('alunos.html', alunos=Aluno.query.order_by(Aluno.nome).all())

@app.route('/secretaria/alunos/editar/<int:id>', methods=['POST'])
def editar_aluno(id):
    if 'usuario_id' not in session: return redirect(url_for('dashboard'))
    aluno = Aluno.query.get_or_404(id)
    aluno.nome = request.form.get('nome'); aluno.email = request.form.get('email')
    aluno.telefone = request.form.get('telefone'); aluno.curso = request.form.get('curso')
    aluno.nivel = request.form.get('nivel'); aluno.status = request.form.get('status')
    aluno.endereco_completo = request.form.get('endereco')
    db.session.commit()
    flash('Dados atualizados!')
    return redirect(url_for('gerenciar_alunos'))

@app.route('/secretaria/alunos/excluir/<int:id>', methods=['POST'])
def excluir_aluno(id):
    if 'usuario_id' not in session: return redirect(url_for('dashboard'))
    aluno = Aluno.query.get_or_404(id)
    if aluno.comprovante_endereco and os.path.exists(os.path.join(app.root_path, 'static', aluno.comprovante_endereco)):
        os.remove(os.path.join(app.root_path, 'static', aluno.comprovante_endereco))
    db.session.delete(aluno)
    db.session.commit()
    flash('Aluno excluído.')
    return redirect(url_for('gerenciar_alunos'))

@app.route('/secretaria/alunos/csv')
def exportar_alunos_csv():
    if 'usuario_id' not in session: return redirect(url_for('dashboard'))
    alunos = Aluno.query.all()
    si = StringIO()
    cw = csv.writer(si, delimiter=';') 
    cw.writerow(['Nome', 'CPF', 'Data de Nascimento', 'Email', 'Telefone', 'Responsável', 'Endereço Completo', 'Curso', 'Nível', 'Status', 'Data da Matrícula'])
    for a in alunos:
        data_nasc = a.data_nascimento.strftime('%d/%m/%Y') if a.data_nascimento else ''
        data_mat = a.data_matricula.strftime('%d/%m/%Y') if a.data_matricula else ''
        cw.writerow([a.nome, a.cpf, data_nasc, a.email, a.telefone, a.nome_responsavel, a.endereco_completo, a.curso, a.nivel, a.status, data_mat])
    return Response('\ufeff' + si.getvalue(), mimetype="text/csv; charset=utf-8", headers={"Content-Disposition": "attachment;filename=relatorio_alunos.csv"})

@app.route('/secretaria/professores', methods=['GET', 'POST'])
def gerenciar_professores():
    if 'usuario_id' not in session: return redirect(url_for('login'))
    if request.method == 'POST':
        data_nasc_str = request.form.get('data_nascimento')
        data_inicio_str = request.form.get('data_inicio')
        data_nasc = datetime.strptime(data_nasc_str, '%Y-%m-%d').date() if data_nasc_str else None
        data_inicio = datetime.strptime(data_inicio_str, '%Y-%m-%d').date() if data_inicio_str else datetime.utcnow().date()
        cpf = request.form.get('cpf')
        arquivo = request.files.get('comprovante')
        caminho_arquivo = None
        if arquivo and arquivo.filename != '':
            extensao = arquivo.filename.split('.')[-1]
            nome_arquivo = f"comprovante_prof_{cpf}.{extensao}"
            arquivo.save(os.path.join(app.config['UPLOAD_FOLDER'], nome_arquivo))
            caminho_arquivo = f"uploads/{nome_arquivo}"

        if Professor.query.filter_by(cpf=cpf).first():
            flash('Erro: CPF já cadastrado.')
        else:
            novo_prof = Professor(nome=request.form.get('nome'), cpf=cpf, email=request.form.get('email'),
                                  data_nascimento=data_nasc, data_inicio=data_inicio,
                                  endereco_completo=request.form.get('endereco'), comprovante_endereco=caminho_arquivo,
                                  telefone=request.form.get('telefone'), curso=request.form.get('curso'), status=request.form.get('status'))
            db.session.add(novo_prof)
            db.session.commit()
            flash('Professor cadastrado!')
            return redirect(url_for('gerenciar_professores'))
    return render_template('professores.html', professores=Professor.query.order_by(Professor.nome).all())

@app.route('/secretaria/professores/editar/<int:id>', methods=['POST'])
def editar_professor(id):
    if 'usuario_id' not in session: return redirect(url_for('dashboard'))
    prof = Professor.query.get_or_404(id)
    prof.nome = request.form.get('nome'); prof.email = request.form.get('email')
    prof.telefone = request.form.get('telefone'); prof.curso = request.form.get('curso')
    prof.status = request.form.get('status'); prof.endereco_completo = request.form.get('endereco')
    db.session.commit()
    flash('Dados do professor atualizados!')
    return redirect(url_for('gerenciar_professores'))

@app.route('/secretaria/professores/excluir/<int:id>', methods=['POST'])
def excluir_professor(id):
    if 'usuario_id' not in session: return redirect(url_for('dashboard'))
    prof = Professor.query.get_or_404(id)
    if prof.comprovante_endereco and os.path.exists(os.path.join(app.root_path, 'static', prof.comprovante_endereco)):
        os.remove(os.path.join(app.root_path, 'static', prof.comprovante_endereco))
    db.session.delete(prof)
    db.session.commit()
    flash('Professor excluído.')
    return redirect(url_for('gerenciar_professores'))

@app.route('/secretaria/professores/csv')
def exportar_professores_csv():
    if 'usuario_id' not in session: return redirect(url_for('dashboard'))
    professores = Professor.query.all()
    si = StringIO()
    cw = csv.writer(si, delimiter=';') 
    cw.writerow(['Nome', 'CPF', 'Data de Nascimento', 'Email', 'Telefone', 'Endereço Completo', 'Instrumento', 'Status', 'Data de Início'])
    for p in professores:
        data_nasc = p.data_nascimento.strftime('%d/%m/%Y') if p.data_nascimento else ''
        data_inicio = p.data_inicio.strftime('%d/%m/%Y') if p.data_inicio else ''
        cw.writerow([p.nome, p.cpf, data_nasc, p.email, p.telefone, p.endereco_completo, p.curso, p.status, data_inicio])
    return Response('\ufeff' + si.getvalue(), mimetype="text/csv; charset=utf-8", headers={"Content-Disposition": "attachment;filename=relatorio_professores.csv"})


# ==============================================================================
# SECRETARIA: AGENDA DE AULAS (O "MATCH" PERFEITO)
# ==============================================================================
@app.route('/secretaria/aulas', methods=['GET', 'POST'])
def gerenciar_aulas():
    if 'usuario_id' not in session or session.get('role') not in ['admin', 'secretaria']:
        flash('Acesso negado.')
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        aluno_id = request.form.get('aluno_id')
        professor_id = request.form.get('professor_id')
        instrumento = request.form.get('instrumento')
        data_aula = datetime.strptime(request.form.get('data_aula'), '%Y-%m-%d').date()
        hora_inicio = datetime.strptime(request.form.get('horario_inicio'), '%H:%M').time()
        hora_fim = datetime.strptime(request.form.get('horario_final'), '%H:%M').time()
        status = request.form.get('status')
        observacoes = request.form.get('observacoes')

        nova_aula = Aula(
            aluno_id=aluno_id, professor_id=professor_id, instrumento=instrumento,
            data_aula=data_aula, horario_inicio=hora_inicio, horario_final=hora_fim,
            status=status, observacoes=observacoes
        )
        db.session.add(nova_aula)
        db.session.commit()
        flash('Aula agendada com sucesso!')
        return redirect(url_for('gerenciar_aulas'))

    # Puxa apenas alunos e professores Ativos para os menus
    alunos = Aluno.query.filter_by(status='Ativo').order_by(Aluno.nome).all()
    professores = Professor.query.filter_by(status='Ativo').order_by(Professor.nome).all()
    aulas = Aula.query.order_by(Aula.data_aula.desc(), Aula.horario_inicio.desc()).all()
    
    return render_template('aulas.html', alunos=alunos, professores=professores, aulas=aulas)

@app.route('/secretaria/aulas/editar/<int:id>', methods=['POST'])
def editar_aula(id):
    if 'usuario_id' not in session: return redirect(url_for('dashboard'))
    aula = Aula.query.get_or_404(id)
    
    aula.aluno_id = request.form.get('aluno_id')
    aula.professor_id = request.form.get('professor_id')
    aula.instrumento = request.form.get('instrumento')
    aula.data_aula = datetime.strptime(request.form.get('data_aula'), '%Y-%m-%d').date()
    aula.horario_inicio = datetime.strptime(request.form.get('horario_inicio'), '%H:%M').time()
    aula.horario_final = datetime.strptime(request.form.get('horario_final'), '%H:%M').time()
    aula.status = request.form.get('status')
    aula.observacoes = request.form.get('observacoes')
    
    db.session.commit()
    flash('Aula atualizada com sucesso!')
    return redirect(url_for('gerenciar_aulas'))

@app.route('/secretaria/aulas/excluir/<int:id>', methods=['POST'])
def excluir_aula(id):
    if 'usuario_id' not in session: return redirect(url_for('dashboard'))
    aula = Aula.query.get_or_404(id)
    db.session.delete(aula)
    db.session.commit()
    flash('Aula excluída.')
    return redirect(url_for('gerenciar_aulas'))

# API para alimentar o Calendário Visual com as aulas
@app.route('/secretaria/aulas/api')
def api_aulas_calendario():
    aulas = Aula.query.all()
    eventos = []
    for aula in aulas:
        cor = '#198754' if aula.status == 'Concluída' else ('#dc3545' if aula.status == 'Cancelada' else '#0d6efd')
        eventos.append({
            'title': f'{aula.aluno.nome} ({aula.instrumento}) - Prof: {aula.professor.nome}',
            'start': f"{aula.data_aula}T{aula.horario_inicio}",
            'end': f"{aula.data_aula}T{aula.horario_final}",
            'color': cor
        })
    return jsonify(eventos)

# ==============================================================================
# MÓDULOS DE ESTÚDIOS: CENTRAL UNIFICADA
# ==============================================================================
@app.route('/estudios', methods=['GET', 'POST'])
def gerenciar_estudios():
    if 'usuario_id' not in session or session.get('role') not in ['admin', 'estudio', 'secretaria']:
        flash('Acesso negado aos estúdios.')
        return redirect(url_for('dashboard'))
        
    if request.method == 'POST':
        tipo_estudio = request.form.get('tipo_estudio')
        data_str = request.form.get('data_agendamento')
        hora_inicio_str = request.form.get('horario_inicio')
        hora_fim_str = request.form.get('horario_final')
        
        data_agendamento = datetime.strptime(data_str, '%Y-%m-%d').date()
        horario_inicio = datetime.strptime(hora_inicio_str, '%H:%M').time()
        horario_final = datetime.strptime(hora_fim_str, '%H:%M').time()

        conflito = AgendamentoEstudio.query.filter(
            AgendamentoEstudio.tipo_estudio == tipo_estudio,
            AgendamentoEstudio.data_agendamento == data_agendamento,
            AgendamentoEstudio.horario_inicio < horario_final,
            AgendamentoEstudio.horario_final > horario_inicio
        ).first()

        if conflito:
            flash(f'Erro: O {tipo_estudio} já está reservado neste dia das {conflito.horario_inicio.strftime("%H:%M")} às {conflito.horario_final.strftime("%H:%M")}.')
            return redirect(url_for('gerenciar_estudios'))

        cpf = request.form.get('cpf')
        arquivo = request.files.get('comprovante')
        caminho_arquivo = None
        if arquivo and arquivo.filename != '':
            extensao = arquivo.filename.split('.')[-1]
            nome_arquivo = f"comprovante_estudio_{cpf}_{data_str}.{extensao}"
            arquivo.save(os.path.join(app.config['UPLOAD_FOLDER'], nome_arquivo))
            caminho_arquivo = f"uploads/{nome_arquivo}"
            
        valor_str = request.form.get('valor', '0')
        valor_limpo = float(valor_str.replace(',', '.')) if valor_str else 0.0

        novo_agendamento = AgendamentoEstudio(
            tipo_estudio=tipo_estudio, nome_cliente=request.form.get('nome_cliente'),
            cpf=cpf, telefone=request.form.get('telefone'), endereco_completo=request.form.get('endereco'),
            comprovante_endereco=caminho_arquivo, data_agendamento=data_agendamento,
            horario_inicio=horario_inicio, horario_final=horario_final, nome_tecnico=request.form.get('nome_tecnico'),
            valor=valor_limpo, status_pagamento=request.form.get('status_pagamento'),
            status_trabalho=request.form.get('status_trabalho'), observacoes=request.form.get('observacoes')
        )
        db.session.add(novo_agendamento)
        db.session.commit()
        flash('Agendamento de estúdio criado com sucesso!')
        return redirect(url_for('gerenciar_estudios'))

    agendamentos = AgendamentoEstudio.query.order_by(AgendamentoEstudio.data_agendamento.desc(), AgendamentoEstudio.horario_inicio.desc()).all()
    return render_template('estudios.html', agendamentos=agendamentos)

@app.route('/estudios/editar/<int:id>', methods=['POST'])
def editar_estudio(id):
    if 'usuario_id' not in session: return redirect(url_for('login'))
    ag = AgendamentoEstudio.query.get_or_404(id)
    
    nova_data = datetime.strptime(request.form.get('data_agendamento'), '%Y-%m-%d').date()
    novo_inicio = datetime.strptime(request.form.get('horario_inicio'), '%H:%M').time()
    novo_fim = datetime.strptime(request.form.get('horario_final'), '%H:%M').time()
    novo_tipo = request.form.get('tipo_estudio')

    conflito = AgendamentoEstudio.query.filter(
        AgendamentoEstudio.id != id,
        AgendamentoEstudio.tipo_estudio == novo_tipo,
        AgendamentoEstudio.data_agendamento == nova_data,
        AgendamentoEstudio.horario_inicio < novo_fim,
        AgendamentoEstudio.horario_final > novo_inicio
    ).first()

    if conflito:
        flash(f'Erro ao editar: Choque de horário com outra reserva ({conflito.horario_inicio.strftime("%H:%M")} às {conflito.horario_final.strftime("%H:%M")}).')
        return redirect(url_for('gerenciar_estudios'))

    ag.tipo_estudio = novo_tipo
    ag.data_agendamento = nova_data
    ag.horario_inicio = novo_inicio
    ag.horario_final = novo_fim
    ag.nome_tecnico = request.form.get('nome_tecnico')
    valor_str = request.form.get('valor', '0')
    ag.valor = float(valor_str.replace(',', '.')) if valor_str else 0.0
    ag.status_pagamento = request.form.get('status_pagamento')
    ag.status_trabalho = request.form.get('status_trabalho')
    ag.observacoes = request.form.get('observacoes')
    
    db.session.commit()
    flash('Agendamento atualizado com sucesso!')
    return redirect(url_for('gerenciar_estudios'))

@app.route('/estudios/excluir/<int:id>', methods=['POST'])
def excluir_estudio(id):
    if 'usuario_id' not in session: return redirect(url_for('login'))
    ag = AgendamentoEstudio.query.get_or_404(id)
    db.session.delete(ag)
    db.session.commit()
    flash('Agendamento excluído.')
    return redirect(url_for('gerenciar_estudios'))

if __name__ == '__main__':
    app.run(debug=True)

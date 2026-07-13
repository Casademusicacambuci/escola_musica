from flask import Flask, render_template, request, redirect, url_for, flash, session, Response, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os
import csv
from io import StringIO

# Importando todas as tabelas (incluindo as novas do Financeiro)
from models import db, Usuario, Aluno, Professor, AgendamentoEstudio, Aula, Fornecedor, Funcionario, ContaReceber, ContaPagar, FluxoCaixa, Produto

app = Flask(__name__)
app.secret_key = 'chave_secreta_cambuci_2026' 
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///cambuci_crm.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

db.init_app(app)

with app.app_context():
    # Recria apenas as tabelas Fornecedor e Funcionario para adicionar os novos campos (como Chave PIX e Endereço)
    Fornecedor.__table__.drop(db.engine, checkfirst=True)
    Funcionario.__table__.drop(db.engine, checkfirst=True)
    
    db.create_all() # Garante que as novas tabelas sejam criadas sem apagar os alunos e estúdios
    
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
# SECRETARIA (ALUNOS, PROFESSORES E AULAS)
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

@app.route('/secretaria/aulas', methods=['GET', 'POST'])
def gerenciar_aulas():
    if 'usuario_id' not in session: return redirect(url_for('dashboard'))
    if request.method == 'POST':
        aluno_id = request.form.get('aluno_id')
        professor_id = request.form.get('professor_id')
        instrumento = request.form.get('instrumento')
        data_aula = datetime.strptime(request.form.get('data_aula'), '%Y-%m-%d').date()
        hora_inicio = datetime.strptime(request.form.get('horario_inicio'), '%H:%M').time()
        hora_fim = datetime.strptime(request.form.get('horario_final'), '%H:%M').time()
        status = request.form.get('status')
        observacoes = request.form.get('observacoes')
        nova_aula = Aula(aluno_id=aluno_id, professor_id=professor_id, instrumento=instrumento,
            data_aula=data_aula, horario_inicio=hora_inicio, horario_final=hora_fim,
            status=status, observacoes=observacoes)
        db.session.add(nova_aula)
        db.session.commit()
        flash('Aula agendada com sucesso!')
        return redirect(url_for('gerenciar_aulas'))

    alunos = Aluno.query.filter_by(status='Ativo').order_by(Aluno.nome).all()
    professores = Professor.query.filter_by(status='Ativo').order_by(Professor.nome).all()
    aulas = Aula.query.order_by(Aula.data_aula.desc(), Aula.horario_inicio.desc()).all()
    return render_template('aulas.html', alunos=alunos, professores=professores, aulas=aulas)

@app.route('/secretaria/aulas/editar/<int:id>', methods=['POST'])
def editar_aula(id):
    if 'usuario_id' not in session: return redirect(url_for('dashboard'))
    aula = Aula.query.get_or_404(id)
    aula.aluno_id = request.form.get('aluno_id'); aula.professor_id = request.form.get('professor_id')
    aula.instrumento = request.form.get('instrumento')
    aula.data_aula = datetime.strptime(request.form.get('data_aula'), '%Y-%m-%d').date()
    aula.horario_inicio = datetime.strptime(request.form.get('horario_inicio'), '%H:%M').time()
    aula.horario_final = datetime.strptime(request.form.get('horario_final'), '%H:%M').time()
    aula.status = request.form.get('status'); aula.observacoes = request.form.get('observacoes')
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
# ESTÚDIOS (INTEGRADO COM FINANCEIRO)
# ==============================================================================
@app.route('/estudios', methods=['GET', 'POST'])
def gerenciar_estudios():
    if 'usuario_id' not in session: return redirect(url_for('login'))
    if request.method == 'POST':
        tipo_estudio = request.form.get('tipo_estudio')
        data_str = request.form.get('data_agendamento')
        hora_inicio_str = request.form.get('horario_inicio')
        hora_fim_str = request.form.get('horario_final')
        data_agendamento = datetime.strptime(data_str, '%Y-%m-%d').date()
        horario_inicio = datetime.strptime(hora_inicio_str, '%H:%M').time()
        horario_final = datetime.strptime(hora_fim_str, '%H:%M').time()

        conflito = AgendamentoEstudio.query.filter(
            AgendamentoEstudio.tipo_estudio == tipo_estudio, AgendamentoEstudio.data_agendamento == data_agendamento,
            AgendamentoEstudio.horario_inicio < horario_final, AgendamentoEstudio.horario_final > horario_inicio
        ).first()

        if conflito:
            flash(f'Erro: O {tipo_estudio} já está reservado neste dia.')
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
        
        # MAGICA DA INTEGRAÇÃO: Se já cadastrou como Concluído, vai pro Financeiro!
        if request.form.get('status_trabalho') == 'Concluído':
            nova_conta = ContaReceber(
                descricao=f"{tipo_estudio} - Cliente: {novo_agendamento.nome_cliente} (Téc: {novo_agendamento.nome_tecnico})",
                modulo_origem="Estúdio", origem_id=novo_agendamento.id, valor=valor_limpo,
                data_vencimento=data_agendamento, status='Pago' if request.form.get('status_pagamento') == 'Pago' else 'Pendente',
                data_pagamento=datetime.utcnow().date() if request.form.get('status_pagamento') == 'Pago' else None
            )
            db.session.add(nova_conta)
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
        AgendamentoEstudio.id != id, AgendamentoEstudio.tipo_estudio == novo_tipo,
        AgendamentoEstudio.data_agendamento == nova_data, AgendamentoEstudio.horario_inicio < novo_fim,
        AgendamentoEstudio.horario_final > novo_inicio
    ).first()

    if conflito:
        flash(f'Erro ao editar: Choque de horário com outra reserva.')
        return redirect(url_for('gerenciar_estudios'))

    ag.tipo_estudio = novo_tipo; ag.data_agendamento = nova_data
    ag.horario_inicio = novo_inicio; ag.horario_final = novo_fim
    ag.nome_tecnico = request.form.get('nome_tecnico')
    valor_str = request.form.get('valor', '0')
    ag.valor = float(valor_str.replace(',', '.')) if valor_str else 0.0
    novo_status_pag = request.form.get('status_pagamento')
    novo_status_trab = request.form.get('status_trabalho')
    ag.status_pagamento = novo_status_pag
    ag.status_trabalho = novo_status_trab
    ag.observacoes = request.form.get('observacoes')
    
    db.session.commit()

    # MÁGICA DA INTEGRAÇÃO: Atualiza ou cria a conta no Financeiro
    conta_existente = ContaReceber.query.filter_by(modulo_origem='Estúdio', origem_id=ag.id).first()
    if conta_existente:
        conta_existente.valor = ag.valor
        conta_existente.status = 'Pago' if novo_status_pag == 'Pago' else 'Pendente'
        if novo_status_pag == 'Pago' and not conta_existente.data_pagamento:
            conta_existente.data_pagamento = datetime.utcnow().date()
        db.session.commit()
    elif not conta_existente and novo_status_trab == 'Concluído':
        nova_conta = ContaReceber(
            descricao=f"{ag.tipo_estudio} - Cliente: {ag.nome_cliente} (Téc: {ag.nome_tecnico})",
            modulo_origem="Estúdio", origem_id=ag.id, valor=ag.valor,
            data_vencimento=ag.data_agendamento, status='Pago' if novo_status_pag == 'Pago' else 'Pendente',
            data_pagamento=datetime.utcnow().date() if novo_status_pag == 'Pago' else None
        )
        db.session.add(nova_conta)
        db.session.commit()

    flash('Agendamento atualizado!')
    return redirect(url_for('gerenciar_estudios'))

@app.route('/estudios/excluir/<int:id>', methods=['POST'])
def excluir_estudio(id):
    if 'usuario_id' not in session: return redirect(url_for('login'))
    ag = AgendamentoEstudio.query.get_or_404(id)
    # Exclui a conta vinculada no financeiro se existir
    conta_vinculada = ContaReceber.query.filter_by(modulo_origem='Estúdio', origem_id=ag.id).first()
    if conta_vinculada:
        db.session.delete(conta_vinculada)
    db.session.delete(ag)
    db.session.commit()
    flash('Agendamento excluído.')
    return redirect(url_for('gerenciar_estudios'))

# ==============================================================================
# MÓDULO 01 - FINANCEIRO & BACKOFFICE
# ==============================================================================
@app.route('/financeiro', methods=['GET'])
def financeiro_dashboard():
    if 'usuario_id' not in session or session.get('role') != 'admin':
        flash('Acesso negado ao Financeiro.')
        return redirect(url_for('dashboard'))
    
    # Cálculos para o Resumo
    contas_receber = ContaReceber.query.order_by(ContaReceber.data_vencimento).all()
    contas_pagar = ContaPagar.query.order_by(ContaPagar.data_vencimento).all()
    
    total_recebido = sum(c.valor for c in contas_receber if c.status == 'Pago')
    total_a_receber = sum(c.valor for c in contas_receber if c.status == 'Pendente')
    
    total_pago = sum(c.valor for c in contas_pagar if c.status == 'Pago')
    total_a_pagar = sum(c.valor for c in contas_pagar if c.status == 'Pendente')
    
    saldo_atual = total_recebido - total_pago

    # Listas para Cadastros
    fornecedores = Fornecedor.query.all()
    funcionarios = Funcionario.query.all()

    return render_template('financeiro.html', 
                           receber=contas_receber, pagar=contas_pagar, 
                           fornecedores=fornecedores, funcionarios=funcionarios,
                           t_recebido=total_recebido, t_a_receber=total_a_receber,
                           t_pago=total_pago, t_a_pagar=total_a_pagar, saldo=saldo_atual)

# Rota para Exportar Planilha Financeira
@app.route('/financeiro/exportar', methods=['POST'])
def exportar_financeiro():
    if 'usuario_id' not in session or session.get('role') != 'admin': return redirect(url_for('dashboard'))
    
    data_inicio_str = request.form.get('data_inicio')
    data_fim_str = request.form.get('data_fim')
    tipo_relatorio = request.form.get('tipo_relatorio')

    data_inicio = datetime.strptime(data_inicio_str, '%Y-%m-%d').date() if data_inicio_str else datetime.min.date()
    data_fim = datetime.strptime(data_fim_str, '%Y-%m-%d').date() if data_fim_str else datetime.max.date()

    si = StringIO()
    cw = csv.writer(si, delimiter=';')

    # Cabeçalho da Planilha
    cw.writerow([f'RELATORIO FINANCEIRO - CASA DE MUSICA CAMBUCI'])
    cw.writerow([f'Periodo: {data_inicio_str} ate {data_fim_str}'])
    cw.writerow([])

    if tipo_relatorio in ['receitas', 'ambos']:
        cw.writerow(['--- ENTRADAS (A RECEBER / RECEBIDAS) ---'])
        cw.writerow(['Vencimento', 'Data Pagamento', 'Origem', 'Descricao', 'Valor (R$)', 'Status'])
        receitas = ContaReceber.query.filter(ContaReceber.data_vencimento >= data_inicio, ContaReceber.data_vencimento <= data_fim).order_by(ContaReceber.data_vencimento).all()
        for r in receitas:
            dp = r.data_pagamento.strftime('%d/%m/%Y') if r.data_pagamento else ''
            cw.writerow([r.data_vencimento.strftime('%d/%m/%Y'), dp, r.modulo_origem, r.descricao, r.valor, r.status])
        cw.writerow([])

    if tipo_relatorio in ['despesas', 'ambos']:
        cw.writerow(['--- SAIDAS (A PAGAR / PAGAS) ---'])
        cw.writerow(['Vencimento', 'Data Pagamento', 'Fornecedor', 'Descricao', 'Valor (R$)', 'Status'])
        despesas = ContaPagar.query.filter(ContaPagar.data_vencimento >= data_inicio, ContaPagar.data_vencimento <= data_fim).order_by(ContaPagar.data_vencimento).all()
        for d in despesas:
            dp = d.data_pagamento.strftime('%d/%m/%Y') if d.data_pagamento else ''
            forn_nome = d.fornecedor.razao_social if d.fornecedor else 'Avulso'
            cw.writerow([d.data_vencimento.strftime('%d/%m/%Y'), dp, forn_nome, d.descricao, d.valor, d.status])

    output = si.getvalue()
    return Response('\ufeff' + output, mimetype="text/csv; charset=utf-8", headers={"Content-Disposition": "attachment;filename=relatorio_financeiro.csv"})

# Rota para cadastrar Nova Conta a Pagar (com Anexo)
@app.route('/financeiro/pagar/nova', methods=['POST'])
def nova_conta_pagar():
    if 'usuario_id' not in session or session.get('role') != 'admin': return redirect(url_for('dashboard'))
    
    arquivo = request.files.get('anexo_nf')
    caminho_arquivo = None
    if arquivo and arquivo.filename != '':
        extensao = arquivo.filename.split('.')[-1]
        nome_arquivo = f"nf_despesa_{datetime.now().strftime('%Y%m%d%H%M%S')}.{extensao}"
        arquivo.save(os.path.join(app.config['UPLOAD_FOLDER'], nome_arquivo))
        caminho_arquivo = f"uploads/{nome_arquivo}"

    valor_str = request.form.get('valor', '0')
    valor_limpo = float(valor_str.replace(',', '.'))
    data_venc = datetime.strptime(request.form.get('data_vencimento'), '%Y-%m-%d').date()

    nova_conta = ContaPagar(
        descricao=request.form.get('descricao'),
        fornecedor_id=request.form.get('fornecedor_id') if request.form.get('fornecedor_id') else None,
        valor=valor_limpo, data_vencimento=data_venc, status=request.form.get('status'),
        data_pagamento=datetime.utcnow().date() if request.form.get('status') == 'Pago' else None,
        anexo_nf=caminho_arquivo
    )
    db.session.add(nova_conta)
    db.session.commit()
    flash('Despesa cadastrada no Contas a Pagar!')
    return redirect(url_for('financeiro_dashboard'))

# Rota para cadastrar Fornecedor Completo
@app.route('/financeiro/fornecedor/novo', methods=['POST'])
def novo_fornecedor():
    if 'usuario_id' not in session or session.get('role') != 'admin': return redirect(url_for('dashboard'))
    novo_forn = Fornecedor(
        razao_social=request.form.get('razao_social'), cnpj_cpf=request.form.get('cnpj_cpf'),
        telefone=request.form.get('telefone'), email=request.form.get('email'),
        endereco_completo=request.form.get('endereco'), chave_pix=request.form.get('chave_pix'),
        categoria=request.form.get('categoria'), status=request.form.get('status')
    )
    db.session.add(novo_forn)
    db.session.commit()
    flash('Fornecedor cadastrado!')
    return redirect(url_for('financeiro_dashboard'))

# Rota para cadastrar Funcionario Completo
@app.route('/financeiro/funcionario/novo', methods=['POST'])
def novo_funcionario():
    if 'usuario_id' not in session or session.get('role') != 'admin': return redirect(url_for('dashboard'))
    
    arquivo = request.files.get('comprovante')
    caminho_arquivo = None
    if arquivo and arquivo.filename != '':
        extensao = arquivo.filename.split('.')[-1]
        nome_arquivo = f"comprovante_func_{request.form.get('cpf')}.{extensao}"
        arquivo.save(os.path.join(app.config['UPLOAD_FOLDER'], nome_arquivo))
        caminho_arquivo = f"uploads/{nome_arquivo}"

    valor_str = request.form.get('salario_base', '0')
    valor_limpo = float(valor_str.replace(',', '.')) if valor_str else 0.0
    
    data_nasc_str = request.form.get('data_nascimento')
    data_nasc = datetime.strptime(data_nasc_str, '%Y-%m-%d').date() if data_nasc_str else None
    
    data_adm_str = request.form.get('data_admissao')
    data_adm = datetime.strptime(data_adm_str, '%Y-%m-%d').date() if data_adm_str else datetime.utcnow().date()

    novo_func = Funcionario(
        nome=request.form.get('nome'), cpf=request.form.get('cpf'), email=request.form.get('email'),
        telefone=request.form.get('telefone'), data_nascimento=data_nasc, endereco_completo=request.form.get('endereco'),
        chave_pix=request.form.get('chave_pix'), cargo=request.form.get('cargo'),
        tipo_contrato=request.form.get('tipo_contrato'), salario_base=valor_limpo,
        data_admissao=data_adm, status=request.form.get('status'), comprovante_endereco=caminho_arquivo
    )
    db.session.add(novo_func)
    db.session.commit()
    flash('Funcionário cadastrado com sucesso!')
    return redirect(url_for('financeiro_dashboard'))

# ==============================================================================
# ESTOQUE (PRODUTOS, LOJA E LANCHONETE)
# ==============================================================================
@app.route('/estoque', methods=['GET'])
def gerenciar_estoque():
    if 'usuario_id' not in session or session.get('role') not in ['admin', 'loja', 'caixa']:
        flash('Acesso negado ao Estoque.')
        return redirect(url_for('dashboard'))
    
    produtos = Produto.query.order_by(Produto.nome).all()
    return render_template('estoque.html', produtos=produtos)

@app.route('/estoque/novo', methods=['POST'])
def novo_produto():
    if 'usuario_id' not in session: return redirect(url_for('dashboard'))
    
    codigo = request.form.get('codigo_barras')
    if Produto.query.filter_by(codigo_barras=codigo).first():
        flash('Erro: Já existe um produto com este código de barras.')
        return redirect(url_for('gerenciar_estoque'))

    pcusto_str = request.form.get('preco_custo', '0')
    pvenda_str = request.form.get('preco_venda', '0')
    
    novo_prod = Produto(
        codigo_barras=codigo,
        nome=request.form.get('nome'),
        categoria=request.form.get('categoria'),
        preco_custo=float(pcusto_str.replace(',', '.')),
        preco_venda=float(pvenda_str.replace(',', '.')),
        quantidade_estoque=int(request.form.get('quantidade_estoque', '0'))
    )
    db.session.add(novo_prod)
    db.session.commit()
    flash('Produto cadastrado com sucesso!')
    return redirect(url_for('gerenciar_estoque'))

@app.route('/estoque/editar/<int:id>', methods=['POST'])
def editar_produto(id):
    if 'usuario_id' not in session: return redirect(url_for('dashboard'))
    p = Produto.query.get_or_404(id)
    
    novo_codigo = request.form.get('codigo_barras')
    conflito = Produto.query.filter(Produto.id != id, Produto.codigo_barras == novo_codigo).first()
    if conflito:
        flash('Erro: Já existe outro produto com este código de barras.')
        return redirect(url_for('gerenciar_estoque'))

    p.codigo_barras = novo_codigo
    p.nome = request.form.get('nome')
    p.categoria = request.form.get('categoria')
    p.preco_custo = float(request.form.get('preco_custo').replace(',', '.'))
    p.preco_venda = float(request.form.get('preco_venda').replace(',', '.'))
    p.quantidade_estoque = int(request.form.get('quantidade_estoque'))
    
    db.session.commit()
    flash('Produto atualizado com sucesso!')
    return redirect(url_for('gerenciar_estoque'))

@app.route('/estoque/excluir/<int:id>', methods=['POST'])
def excluir_produto(id):
    if 'usuario_id' not in session: return redirect(url_for('dashboard'))
    p = Produto.query.get_or_404(id)
    db.session.delete(p)
    db.session.commit()
    flash('Produto excluído.')
    return redirect(url_for('gerenciar_estoque'))

if __name__ == '__main__':
    app.run(debug=True)

from flask import Flask, render_template, request, redirect, url_for, flash, session, Response, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os
import csv
from io import StringIO

from models import db, Usuario, Aluno, Professor, AgendamentoEstudio, Aula, Fornecedor, Funcionario, ContaReceber, ContaPagar, FluxoCaixa, Produto, OrdemServico

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
# SECRETARIA E ALUNOS 
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

        v_mens = request.form.get('valor_mensalidade', '0')
        valor_mensalidade = float(v_mens.replace(',', '.')) if v_mens else 0.0

        if Aluno.query.filter_by(cpf=cpf).first():
            flash('Erro: CPF já cadastrado.')
        else:
            novo_aluno = Aluno(nome=request.form.get('nome'), cpf=cpf, email=request.form.get('email'),
                               data_nascimento=data_nasc, nome_responsavel=request.form.get('responsavel'),
                               endereco_completo=request.form.get('endereco'), comprovante_endereco=caminho_arquivo,
                               telefone=request.form.get('telefone'), curso=request.form.get('curso'),
                               nivel=request.form.get('nivel'), data_matricula=data_mat, status=request.form.get('status'),
                               valor_mensalidade=valor_mensalidade)
            db.session.add(novo_aluno)
            db.session.flush() 
            
            mes_atual = data_mat.month
            ano_atual = data_mat.year
            for mes in range(mes_atual, 13):
                vencimento = datetime(ano_atual, mes, 10).date()
                nova_conta = ContaReceber(
                    descricao=f"Mensalidade {mes:02d}/{ano_atual} - {novo_aluno.nome}",
                    modulo_origem="Mensalidade", origem_id=novo_aluno.id,
                    valor=valor_mensalidade, data_vencimento=vencimento, status="Pendente"
                )
                db.session.add(nova_conta)
                
            db.session.commit()
            flash('Aluno matriculado e carnê de mensalidades gerado até dezembro!')
            return redirect(url_for('gerenciar_alunos'))
            
    alunos = Aluno.query.order_by(Aluno.nome).all()
    contas_alunos = {}
    for a in alunos:
        contas_alunos[a.id] = ContaReceber.query.filter_by(modulo_origem='Mensalidade', origem_id=a.id).order_by(ContaReceber.data_vencimento).all()
    return render_template('alunos.html', alunos=alunos, contas_alunos=contas_alunos)

@app.route('/secretaria/alunos/editar/<int:id>', methods=['POST'])
def editar_aluno(id):
    if 'usuario_id' not in session: return redirect(url_for('dashboard'))
    aluno = Aluno.query.get_or_404(id)
    aluno.nome = request.form.get('nome') or aluno.nome
    aluno.email = request.form.get('email') or aluno.email
    aluno.telefone = request.form.get('telefone') or aluno.telefone
    aluno.curso = request.form.get('curso') or aluno.curso
    aluno.nivel = request.form.get('nivel') or aluno.nivel
    aluno.status = request.form.get('status') or aluno.status
    aluno.endereco_completo = request.form.get('endereco') or aluno.endereco_completo
    
    v_mens = request.form.get('valor_mensalidade')
    if v_mens:
        novo_valor = float(v_mens.replace(',', '.'))
        if novo_valor != aluno.valor_mensalidade:
            aluno.valor_mensalidade = novo_valor
            pendentes = ContaReceber.query.filter_by(modulo_origem="Mensalidade", origem_id=aluno.id, status="Pendente").all()
            for p in pendentes:
                p.valor = novo_valor

    db.session.commit()
    flash('Dados do aluno atualizados com sucesso!')
    return redirect(url_for('gerenciar_alunos'))

@app.route('/secretaria/alunos/excluir/<int:id>', methods=['POST'])
def excluir_aluno(id):
    if 'usuario_id' not in session: return redirect(url_for('dashboard'))
    aluno = Aluno.query.get_or_404(id)
    ContaReceber.query.filter_by(modulo_origem='Mensalidade', origem_id=aluno.id, status='Pendente').delete()
    if aluno.comprovante_endereco and os.path.exists(os.path.join(app.root_path, 'static', aluno.comprovante_endereco)):
        os.remove(os.path.join(app.root_path, 'static', aluno.comprovante_endereco))
    db.session.delete(aluno)
    db.session.commit()
    flash('Aluno e faturas pendentes excluídos.')
    return redirect(url_for('gerenciar_alunos'))

@app.route('/secretaria/alunos/csv')
def exportar_alunos_csv():
    if 'usuario_id' not in session: return redirect(url_for('dashboard'))
    alunos = Aluno.query.all()
    si = StringIO(); cw = csv.writer(si, delimiter=';') 
    cw.writerow(['Nome', 'CPF', 'Mensalidade', 'Email', 'Telefone', 'Responsável', 'Curso', 'Status'])
    for a in alunos:
        cw.writerow([a.nome, a.cpf, a.valor_mensalidade, a.email, a.telefone, a.nome_responsavel, a.curso, a.status])
    return Response('\ufeff' + si.getvalue(), mimetype="text/csv; charset=utf-8", headers={"Content-Disposition": "attachment;filename=relatorio_alunos.csv"})

@app.route('/secretaria/professores', methods=['GET', 'POST'])
def gerenciar_professores():
    if 'usuario_id' not in session: return redirect(url_for('login'))
    if request.method == 'POST':
        data_nasc_str = request.form.get('data_nascimento')
        data_nasc = datetime.strptime(data_nasc_str, '%Y-%m-%d').date() if data_nasc_str else None
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
                                  data_nascimento=data_nasc, endereco_completo=request.form.get('endereco'),
                                  telefone=request.form.get('telefone'), curso=request.form.get('curso'), 
                                  status=request.form.get('status'), comprovante_endereco=caminho_arquivo)
            db.session.add(novo_prof)
            db.session.commit()
            flash('Professor cadastrado com sucesso!')
            return redirect(url_for('gerenciar_professores'))
    return render_template('professores.html', professores=Professor.query.order_by(Professor.nome).all())

@app.route('/secretaria/professores/editar/<int:id>', methods=['POST'])
def editar_professor(id):
    if 'usuario_id' not in session: return redirect(url_for('dashboard'))
    prof = Professor.query.get_or_404(id)
    prof.nome = request.form.get('nome') or prof.nome
    prof.email = request.form.get('email') or prof.email
    prof.telefone = request.form.get('telefone') or prof.telefone
    prof.curso = request.form.get('curso') or prof.curso
    prof.status = request.form.get('status') or prof.status
    prof.endereco_completo = request.form.get('endereco') or prof.endereco_completo
    db.session.commit()
    flash('Dados atualizados!')
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
    si = StringIO(); cw = csv.writer(si, delimiter=';') 
    cw.writerow(['Nome', 'CPF', 'Data de Nascimento', 'Email', 'Telefone', 'Curso', 'Status'])
    for p in professores:
        data_nasc = p.data_nascimento.strftime('%d/%m/%Y') if p.data_nascimento else ''
        cw.writerow([p.nome, p.cpf, data_nasc, p.email, p.telefone, p.curso, p.status])
    return Response('\ufeff' + si.getvalue(), mimetype="text/csv; charset=utf-8", headers={"Content-Disposition": "attachment;filename=relatorio_professores.csv"})

@app.route('/secretaria/aulas', methods=['GET', 'POST'])
def gerenciar_aulas():
    if 'usuario_id' not in session: return redirect(url_for('dashboard'))
    if request.method == 'POST':
        aluno_id = request.form.get('aluno_id'); professor_id = request.form.get('professor_id')
        instrumento = request.form.get('instrumento')
        data_aula = datetime.strptime(request.form.get('data_aula'), '%Y-%m-%d').date()
        hora_inicio = datetime.strptime(request.form.get('horario_inicio'), '%H:%M').time()
        hora_fim = datetime.strptime(request.form.get('horario_final'), '%H:%M').time()
        status = request.form.get('status')
        nova_aula = Aula(aluno_id=aluno_id, professor_id=professor_id, instrumento=instrumento,
            data_aula=data_aula, horario_inicio=hora_inicio, horario_final=hora_fim,
            status=status, observacoes=request.form.get('observacoes'))
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
    aula.aluno_id = request.form.get('aluno_id')
    aula.professor_id = request.form.get('professor_id')
    aula.instrumento = request.form.get('instrumento')
    aula.data_aula = datetime.strptime(request.form.get('data_aula'), '%Y-%m-%d').date()
    aula.horario_inicio = datetime.strptime(request.form.get('horario_inicio'), '%H:%M').time()
    aula.horario_final = datetime.strptime(request.form.get('horario_final'), '%H:%M').time()
    aula.status = request.form.get('status')
    aula.observacoes = request.form.get('observacoes')
    db.session.commit()
    flash('Aula atualizada!')
    return redirect(url_for('gerenciar_aulas'))

@app.route('/secretaria/aulas/excluir/<int:id>', methods=['POST'])
def excluir_aula(id):
    if 'usuario_id' not in session: return redirect(url_for('dashboard'))
    db.session.delete(Aula.query.get_or_404(id))
    db.session.commit()
    return redirect(url_for('gerenciar_aulas'))

@app.route('/secretaria/aulas/api')
def api_aulas_calendario():
    eventos = []
    for aula in Aula.query.all():
        cor = '#198754' if aula.status == 'Concluída' else ('#dc3545' if aula.status == 'Cancelada' else '#0d6efd')
        eventos.append({
            'title': f'{aula.aluno.nome} - Prof: {aula.professor.nome}',
            'start': f"{aula.data_aula}T{aula.horario_inicio}",
            'end': f"{aula.data_aula}T{aula.horario_final}",
            'color': cor
        })
    return jsonify(eventos)

# ==============================================================================
# ESTÚDIOS
# ==============================================================================
@app.route('/estudios', methods=['GET', 'POST'])
def gerenciar_estudios():
    if 'usuario_id' not in session: return redirect(url_for('login'))
    if request.method == 'POST':
        tipo_estudio = request.form.get('tipo_estudio')
        data_str = request.form.get('data_agendamento')
        data_agendamento = datetime.strptime(data_str, '%Y-%m-%d').date()
        horario_inicio = datetime.strptime(request.form.get('horario_inicio'), '%H:%M').time()
        horario_final = datetime.strptime(request.form.get('horario_final'), '%H:%M').time()

        valor_limpo = float(request.form.get('valor', '0').replace(',', '.'))
        novo_agendamento = AgendamentoEstudio(
            tipo_estudio=tipo_estudio, nome_cliente=request.form.get('nome_cliente'),
            cpf=request.form.get('cpf'), telefone=request.form.get('telefone'), endereco_completo=request.form.get('endereco'),
            data_agendamento=data_agendamento, horario_inicio=horario_inicio, horario_final=horario_final, 
            nome_tecnico=request.form.get('nome_tecnico'), valor=valor_limpo, 
            status_pagamento=request.form.get('status_pagamento'), status_trabalho=request.form.get('status_trabalho'), 
            observacoes=request.form.get('observacoes')
        )
        db.session.add(novo_agendamento)
        db.session.commit()
        
        if request.form.get('status_trabalho') == 'Concluído':
            nova_conta = ContaReceber(
                descricao=f"{tipo_estudio} - Cliente: {novo_agendamento.nome_cliente}",
                modulo_origem="Estúdio", origem_id=novo_agendamento.id, valor=valor_limpo,
                data_vencimento=data_agendamento, status='Pago' if request.form.get('status_pagamento') == 'Pago' else 'Pendente',
                data_pagamento=datetime.utcnow().date() if request.form.get('status_pagamento') == 'Pago' else None
            )
            db.session.add(nova_conta)
            db.session.commit()
        flash('Agendamento criado! Se for a receber, já pode ser cobrado no Caixa PDV.')
        return redirect(url_for('gerenciar_estudios'))
    return render_template('estudios.html', agendamentos=AgendamentoEstudio.query.order_by(AgendamentoEstudio.data_agendamento.desc()).all())

@app.route('/estudios/editar/<int:id>', methods=['POST'])
def editar_estudio(id):
    if 'usuario_id' not in session: return redirect(url_for('login'))
    ag = AgendamentoEstudio.query.get_or_404(id)
    ag.tipo_estudio = request.form.get('tipo_estudio')
    ag.data_agendamento = datetime.strptime(request.form.get('data_agendamento'), '%Y-%m-%d').date()
    ag.horario_inicio = datetime.strptime(request.form.get('horario_inicio'), '%H:%M').time()
    ag.horario_final = datetime.strptime(request.form.get('horario_final'), '%H:%M').time()
    ag.valor = float(request.form.get('valor', '0').replace(',', '.'))
    ag.status_pagamento = request.form.get('status_pagamento')
    ag.status_trabalho = request.form.get('status_trabalho')
    db.session.commit()

    conta = ContaReceber.query.filter_by(modulo_origem='Estúdio', origem_id=ag.id).first()
    if conta:
        conta.valor = ag.valor
        conta.status = 'Pago' if ag.status_pagamento == 'Pago' else 'Pendente'
        if ag.status_pagamento == 'Pago' and not conta.data_pagamento:
            conta.data_pagamento = datetime.utcnow().date()
        db.session.commit()
    elif not conta and ag.status_trabalho == 'Concluído':
        nova_conta = ContaReceber(
            descricao=f"{ag.tipo_estudio} - Cliente: {ag.nome_cliente}",
            modulo_origem="Estúdio", origem_id=ag.id, valor=ag.valor,
            data_vencimento=ag.data_agendamento, status='Pago' if ag.status_pagamento == 'Pago' else 'Pendente',
            data_pagamento=datetime.utcnow().date() if ag.status_pagamento == 'Pago' else None
        )
        db.session.add(nova_conta)
        db.session.commit()
    return redirect(url_for('gerenciar_estudios'))

@app.route('/estudios/excluir/<int:id>', methods=['POST'])
def excluir_estudio(id):
    if 'usuario_id' not in session: return redirect(url_for('login'))
    db.session.delete(AgendamentoEstudio.query.get_or_404(id))
    db.session.commit()
    return redirect(url_for('gerenciar_estudios'))

# ==============================================================================
# MÓDULO FINANCEIRO
# ==============================================================================
@app.route('/financeiro', methods=['GET'])
def financeiro_dashboard():
    if 'usuario_id' not in session or session.get('role') != 'admin':
        flash('Acesso negado ao Financeiro.')
        return redirect(url_for('dashboard'))
    
    hoje = datetime.utcnow().date()
    if hoje.month == 12:
        limite_mes = datetime(hoje.year + 1, 1, 1).date()
    else:
        limite_mes = datetime(hoje.year, hoje.month + 1, 1).date()

    contas_receber_todas = ContaReceber.query.order_by(ContaReceber.data_vencimento).all()
    contas_pagar = ContaPagar.query.order_by(ContaPagar.data_vencimento).all()
    
    contas_receber = [c for c in contas_receber_todas if c.modulo_origem != 'Sangria / Despesa']
    
    total_recebido = sum(c.valor for c in contas_receber if c.status == 'Pago')
    total_a_receber = sum(c.valor for c in contas_receber if c.status == 'Pendente')
    total_pago = sum(c.valor for c in contas_pagar if c.status == 'Pago')
    total_a_pagar = sum(c.valor for c in contas_pagar if c.status == 'Pendente')
    saldo_atual = total_recebido - total_pago

    inadimplentes = [c for c in contas_receber if c.status == 'Pendente' and c.data_vencimento < hoje]

    receber_atual = [c for c in contas_receber if c.data_vencimento < limite_mes]
    receber_futuro = [c for c in contas_receber if c.data_vencimento >= limite_mes]

    professores = Professor.query.filter_by(status='Ativo').all()
    repasse_profs = []
    for prof in professores:
        aulas_concluidas = Aula.query.filter_by(professor_id=prof.id, status='Concluída').all()
        aulas_mes = [a for a in aulas_concluidas if a.data_aula.month == hoje.month and a.data_aula.year == hoje.year]
        
        comissao_total = 0.0
        for aula in aulas_mes:
            if aula.aluno and aula.aluno.valor_mensalidade:
                comissao_total += (aula.aluno.valor_mensalidade * 0.40) / 4.0
        
        if comissao_total > 0:
            repasse_profs.append({
                'nome': prof.nome,
                'qtd_aulas': len(aulas_mes),
                'comissao': comissao_total
            })

    return render_template('financeiro.html', 
                           receber_atual=receber_atual, receber_futuro=receber_futuro, pagar=contas_pagar, 
                           fornecedores=Fornecedor.query.all(), funcionarios=Funcionario.query.all(),
                           t_recebido=total_recebido, t_a_receber=total_a_receber,
                           t_pago=total_pago, t_a_pagar=total_a_pagar, saldo=saldo_atual,
                           inadimplentes=inadimplentes, repasse_profs=repasse_profs)

@app.route('/financeiro/repasse/pagar', methods=['POST'])
def registrar_repasse():
    if 'usuario_id' not in session: return redirect(url_for('dashboard'))
    nome_prof = request.form.get('nome_professor')
    valor_comissao = float(request.form.get('valor_comissao', '0'))
    mes_atual = datetime.utcnow().strftime('%m/%Y')
    
    nova_despesa = ContaPagar(
        descricao=f"Repasse Prof(a) {nome_prof} - Mês {mes_atual}",
        valor=valor_comissao,
        data_vencimento=datetime.utcnow().date(),
        status="Pendente"
    )
    db.session.add(nova_despesa)
    db.session.commit()
    flash(f'Pagamento gerado! Vá na aba "A Pagar (Saídas)" para visualizar ou editar.')
    return redirect(url_for('financeiro_dashboard'))

@app.route('/financeiro/exportar', methods=['POST'])
def exportar_financeiro():
    if 'usuario_id' not in session: return redirect(url_for('dashboard'))
    d_inicio_str = request.form.get('data_inicio')
    d_fim_str = request.form.get('data_fim')
    d_inicio = datetime.strptime(d_inicio_str, '%Y-%m-%d').date() if d_inicio_str else datetime.utcnow().date()
    d_fim = datetime.strptime(d_fim_str, '%Y-%m-%d').date() if d_fim_str else datetime.utcnow().date()
    
    tipo = request.form.get('tipo_relatorio')
    filtro_modulo = request.form.get('filtro_modulo', 'Todos')

    si = StringIO()
    cw = csv.writer(si, delimiter=';')
    cw.writerow(['TIPO', 'VENCIMENTO', 'PAGAMENTO', 'MÓDULO/ORIGEM', 'DESCRIÇÃO', 'VALOR (R$)', 'STATUS'])
    
    if tipo in ['receitas', 'ambos']:
        query_receitas = ContaReceber.query.filter(ContaReceber.data_vencimento >= d_inicio, ContaReceber.data_vencimento <= d_fim, ContaReceber.modulo_origem != 'Sangria / Despesa')
        if filtro_modulo != 'Todos':
            query_receitas = query_receitas.filter(ContaReceber.modulo_origem == filtro_modulo)
            
        for r in query_receitas.order_by(ContaReceber.data_vencimento).all():
            dp = r.data_pagamento.strftime('%d/%m/%Y') if r.data_pagamento else ''
            valor_br = f"{r.valor:.2f}".replace('.', ',')
            cw.writerow(['ENTRADA', r.data_vencimento.strftime('%d/%m/%Y'), dp, r.modulo_origem, r.descricao, valor_br, r.status])
            
    if tipo in ['despesas', 'ambos']:
        if filtro_modulo == 'Todos':
            for d in ContaPagar.query.filter(ContaPagar.data_vencimento >= d_inicio, ContaPagar.data_vencimento <= d_fim).order_by(ContaPagar.data_vencimento).all():
                dp = d.data_pagamento.strftime('%d/%m/%Y') if d.data_pagamento else ''
                valor_br = f"{d.valor:.2f}".replace('.', ',')
                cw.writerow(['SAÍDA', d.data_vencimento.strftime('%d/%m/%Y'), dp, 'Despesa / Repasse', d.descricao, valor_br, d.status])

    return Response('\ufeff' + si.getvalue(), mimetype="text/csv; charset=utf-8", headers={"Content-Disposition": f"attachment;filename=relatorio_financeiro.csv"})

@app.route('/financeiro/receber/nova', methods=['POST'])
def nova_conta_receber():
    if 'usuario_id' not in session: return redirect(url_for('dashboard'))
    valor_limpo = float(request.form.get('valor', '0').replace(',', '.'))
    data_venc = datetime.strptime(request.form.get('data_vencimento'), '%Y-%m-%d').date()
    nova_conta = ContaReceber(
        descricao=request.form.get('descricao'),
        modulo_origem=request.form.get('modulo_origem', 'Mensalidade'),
        valor=valor_limpo, data_vencimento=data_venc, status=request.form.get('status'),
        data_pagamento=datetime.utcnow().date() if request.form.get('status') == 'Pago' else None
    )
    db.session.add(nova_conta)
    db.session.commit()
    flash('Receita lançada com sucesso!')
    return redirect(url_for('financeiro_dashboard'))

@app.route('/financeiro/pagar/nova', methods=['POST'])
def nova_conta_pagar():
    if 'usuario_id' not in session: return redirect(url_for('dashboard'))
    valor_limpo = float(request.form.get('valor', '0').replace(',', '.'))
    data_venc = datetime.strptime(request.form.get('data_vencimento'), '%Y-%m-%d').date()
    nova_conta = ContaPagar(
        descricao=request.form.get('descricao'), fornecedor_id=request.form.get('fornecedor_id') or None,
        valor=valor_limpo, data_vencimento=data_venc, status=request.form.get('status'),
        data_pagamento=datetime.utcnow().date() if request.form.get('status') == 'Pago' else None
    )
    db.session.add(nova_conta)
    db.session.commit()
    flash('Despesa lançada com sucesso!')
    return redirect(url_for('financeiro_dashboard'))

@app.route('/financeiro/pagar/confirmar/<int:id>', methods=['POST'])
def confirmar_pagamento(id):
    if 'usuario_id' not in session: return redirect(url_for('dashboard'))
    conta = ContaPagar.query.get_or_404(id)
    conta.status = 'Pago'
    conta.data_pagamento = datetime.utcnow().date()
    db.session.commit()
    flash('Pagamento confirmado com sucesso!')
    return redirect(url_for('financeiro_dashboard'))

@app.route('/financeiro/pagar/excluir/<int:id>', methods=['POST'])
def excluir_conta_pagar(id):
    if 'usuario_id' not in session: return redirect(url_for('dashboard'))
    conta = ContaPagar.query.get_or_404(id)
    db.session.delete(conta)
    db.session.commit()
    flash('Conta a pagar excluída!')
    return redirect(url_for('financeiro_dashboard'))

@app.route('/financeiro/receber/excluir/<int:id>', methods=['POST'])
def excluir_conta_receber(id):
    if 'usuario_id' not in session: return redirect(url_for('dashboard'))
    conta = ContaReceber.query.get_or_404(id)
    db.session.delete(conta)
    db.session.commit()
    flash('Cobrança excluída!')
    return redirect(url_for('financeiro_dashboard'))

# ==============================================================================
# ESTOQUE
# ==============================================================================
@app.route('/estoque', methods=['GET'])
def gerenciar_estoque():
    if 'usuario_id' not in session: return redirect(url_for('dashboard'))
    return render_template('estoque.html', produtos=Produto.query.order_by(Produto.nome).all())

@app.route('/estoque/novo', methods=['POST'])
def novo_produto():
    if 'usuario_id' not in session: return redirect(url_for('dashboard'))
    codigo = request.form.get('codigo_barras')
    if Produto.query.filter_by(codigo_barras=codigo).first():
        flash('Erro: Já existe um produto com este código.')
        return redirect(url_for('gerenciar_estoque'))
    novo_prod = Produto(
        codigo_barras=codigo, nome=request.form.get('nome'), categoria=request.form.get('categoria'),
        preco_custo=float(request.form.get('preco_custo').replace(',', '.')),
        preco_venda=float(request.form.get('preco_venda').replace(',', '.')),
        quantidade_estoque=int(request.form.get('quantidade_estoque', '0'))
    )
    db.session.add(novo_prod)
    db.session.commit()
    return redirect(url_for('gerenciar_estoque'))

@app.route('/estoque/editar/<int:id>', methods=['POST'])
def editar_produto(id):
    if 'usuario_id' not in session: return redirect(url_for('dashboard'))
    p = Produto.query.get_or_404(id)
    p.codigo_barras = request.form.get('codigo_barras')
    p.nome = request.form.get('nome'); p.categoria = request.form.get('categoria')
    p.preco_custo = float(request.form.get('preco_custo').replace(',', '.')); p.preco_venda = float(request.form.get('preco_venda').replace(',', '.'))
    p.quantidade_estoque = int(request.form.get('quantidade_estoque'))
    db.session.commit()
    return redirect(url_for('gerenciar_estoque'))

@app.route('/estoque/excluir/<int:id>', methods=['POST'])
def excluir_produto(id):
    if 'usuario_id' not in session: return redirect(url_for('dashboard'))
    db.session.delete(Produto.query.get_or_404(id))
    db.session.commit()
    return redirect(url_for('gerenciar_estoque'))

# ==============================================================================
# CAIXA PDV (SEM HÍFEN NO CÓDIGO)
# ==============================================================================
@app.route('/caixa', methods=['GET'])
def caixa_pdv():
    if 'usuario_id' not in session: return redirect(url_for('dashboard'))
    return render_template('caixa.html')

@app.route('/api/produto/<codigo>')
def api_buscar_produto(codigo):
    if 'usuario_id' not in session: return jsonify({'erro': 'Não autorizado'})
    codigo = codigo.strip().upper()
    
    # Reconhece REC1, REC2 sem traço
    if codigo.startswith('REC'):
        try:
            conta_id = int(codigo[3:])
            conta = ContaReceber.query.get(conta_id)
            if conta:
                if conta.status == 'Pago': return jsonify({'erro': 'Esta cobrança já consta como PAGA no Financeiro!'})
                return jsonify({'id': f'REC{conta.id}', 'nome': f"PAGAMENTO: {conta.modulo_origem} ({conta.descricao})", 'preco': conta.valor, 'tipo': 'receita'})
        except: pass

    # Reconhece PAG1, PAG2 sem traço
    if codigo.startswith('PAG'):
        try:
            conta_id = int(codigo[3:])
            conta = ContaPagar.query.get(conta_id)
            if conta:
                if conta.status == 'Pago': return jsonify({'erro': 'Esta despesa já consta como PAGA!'})
                return jsonify({'id': f'PAG{conta.id}', 'nome': f"SAÍDA DE CAIXA: {conta.descricao}", 'preco': -abs(conta.valor), 'tipo': 'despesa'})
        except: pass

    produto = Produto.query.filter_by(codigo_barras=codigo).first()
    if produto:
        if produto.quantidade_estoque <= 0: return jsonify({'erro': f'Produto "{produto.nome}" sem estoque!'})
        return jsonify({'id': produto.id, 'nome': produto.nome, 'preco': produto.preco_venda, 'tipo': 'produto'})
    return jsonify({'erro': 'Código não encontrado. Verifique se digitou certo.'})

@app.route('/caixa/finalizar', methods=['POST'])
def finalizar_venda():
    if 'usuario_id' not in session: return jsonify({'sucesso': False})
    dados = request.get_json()
    itens = dados.get('itens', [])
    forma_pagamento = dados.get('forma_pagamento', 'Dinheiro')
    if not itens: return jsonify({'sucesso': False, 'erro': 'Carrinho vazio'})

    produtos_fisicos = []
    for item in itens:
        item_id = str(item['id'])
        if item_id.startswith('REC'):
            conta = ContaReceber.query.get(int(item_id[3:]))
            if conta:
                conta.status = 'Pago'; conta.data_pagamento = datetime.utcnow().date(); conta.forma_pagamento = forma_pagamento
        elif item_id.startswith('PAG'):
            conta_p = ContaPagar.query.get(int(item_id[3:]))
            if conta_p:
                conta_p.status = 'Pago'
                conta_p.data_pagamento = datetime.utcnow().date()
                db.session.add(ContaReceber(
                    descricao=f"SAÍDA PDV: Pagamento {conta_p.descricao}", modulo_origem="Sangria / Despesa", valor=-abs(conta_p.valor),
                    data_vencimento=datetime.utcnow().date(), data_pagamento=datetime.utcnow().date(),
                    status="Pago", forma_pagamento=forma_pagamento
                ))
        else:
            produto = Produto.query.get(item['id'])
            if produto:
                produto.quantidade_estoque -= item['quantidade']
                produtos_fisicos.append(f"{item['quantidade']}x {produto.nome}")
                
    if produtos_fisicos:
        total_produtos = sum(float(i['preco']) * int(i['quantidade']) for i in itens if not str(i['id']).startswith('REC') and not str(i['id']).startswith('PAG'))
        if total_produtos > 0:
            db.session.add(ContaReceber(
                descricao="Venda PDV: " + ", ".join(produtos_fisicos), modulo_origem="Loja / PDV", valor=total_produtos,
                data_vencimento=datetime.utcnow().date(), data_pagamento=datetime.utcnow().date(),
                status="Pago", forma_pagamento=forma_pagamento
            ))
            
    db.session.commit()
    return jsonify({'sucesso': True})

@app.route('/caixa/fechamento', methods=['GET'])
def fechamento_caixa():
    if 'usuario_id' not in session: return jsonify({'erro': 'Não autorizado'})
    recebimentos_hoje = ContaReceber.query.filter_by(data_pagamento=datetime.utcnow().date(), status='Pago').all()
    resumo = {'Dinheiro': 0.0, 'Pix': 0.0, 'Cartao_Credito': 0.0, 'Cartao_Debito': 0.0, 'Total': 0.0}
    for r in recebimentos_hoje:
        forma = r.forma_pagamento
        if forma == 'Pix': resumo['Pix'] += r.valor
        elif forma == 'Cartão de Crédito': resumo['Cartao_Credito'] += r.valor
        elif forma == 'Cartão de Débito': resumo['Cartao_Debito'] += r.valor
        else: resumo['Dinheiro'] += r.valor 
        resumo['Total'] += r.valor
    return jsonify(resumo)

# ==============================================================================
# MÓDULO LUTHIER / OFICINA
# ==============================================================================
@app.route('/luthier', methods=['GET'])
def luthier_dashboard():
    if 'usuario_id' not in session: return redirect(url_for('dashboard'))
    ordens = OrdemServico.query.order_by(OrdemServico.data_abertura.desc()).all()
    return render_template('luthier.html', ordens=ordens)

@app.route('/luthier/nova', methods=['POST'])
def luthier_nova_os():
    if 'usuario_id' not in session: return redirect(url_for('dashboard'))
    
    fotos = []
    for i in range(1, 5):
        arquivo = request.files.get(f'foto_{i}')
        if arquivo and arquivo.filename != '':
            nome_arquivo = f"os_foto_{i}_{datetime.now().strftime('%Y%m%d%H%M%S')}.jpg"
            arquivo.save(os.path.join(app.config['UPLOAD_FOLDER'], nome_arquivo))
            fotos.append(f"uploads/{nome_arquivo}")
        else:
            fotos.append(None)

    nova_os = OrdemServico(
        cliente_nome=request.form.get('cliente_nome'), cliente_cpf=request.form.get('cliente_cpf'),
        cliente_telefone=request.form.get('cliente_telefone'), cliente_email=request.form.get('cliente_email'),
        cliente_endereco=request.form.get('cliente_endereco'),
        instrumento_tipo=request.form.get('instrumento_tipo'), instrumento_marca=request.form.get('instrumento_marca'),
        instrumento_modelo=request.form.get('instrumento_modelo'), descricao_problema=request.form.get('descricao_problema'),
        foto_1=fotos[0], foto_2=fotos[1], foto_3=fotos[2], foto_4=fotos[3],
        video_link=request.form.get('video_link')
    )
    db.session.add(nova_os)
    db.session.commit()
    flash('Ordem de Serviço criada com sucesso! Ela está na aba "Em Análise".')
    return redirect(url_for('luthier_dashboard'))

@app.route('/luthier/orcamento/<int:id>', methods=['POST'])
def luthier_orcamento(id):
    if 'usuario_id' not in session: return redirect(url_for('dashboard'))
    os = OrdemServico.query.get_or_404(id)
    
    os.solucao_sugerida = request.form.get('solucao_sugerida')
    
    v_mao_obra = request.form.get('valor_mao_de_obra', '0').replace(',', '.')
    os.valor_mao_de_obra = float(v_mao_obra) if v_mao_obra else 0.0
    
    v_pecas = request.form.get('valor_pecas', '0').replace(',', '.')
    os.valor_pecas = float(v_pecas) if v_pecas else 0.0
    
    os.prazo_estimado = request.form.get('prazo_estimado')
    
    data_ent_str = request.form.get('data_entrega')
    if data_ent_str:
        os.data_entrega = datetime.strptime(data_ent_str, '%Y-%m-%d').date()
        
    os.luthier_responsavel = request.form.get('luthier_responsavel')
    os.status = 'Aguardando Aprovação'
    
    db.session.commit()
    flash('Orçamento salvo! Clique em "Enviar Zap" para falar com o cliente.')
    return redirect(url_for('luthier_dashboard'))

@app.route('/luthier/aprovar/<int:id>', methods=['POST'])
def luthier_aprovar(id):
    if 'usuario_id' not in session: return redirect(url_for('dashboard'))
    os = OrdemServico.query.get_or_404(id)
    os.status = 'Em Manutenção'
    
    valor_total = (os.valor_mao_de_obra or 0) + (os.valor_pecas or 0)
    valor_sinal = valor_total / 2.0
    
    db.session.add(ContaReceber(
        descricao=f"Sinal (50%) OS-{os.id} Luthier ({os.cliente_nome})",
        modulo_origem="Luthier", origem_id=os.id, valor=valor_sinal,
        data_vencimento=datetime.utcnow().date(), status="Pendente"
    ))
    db.session.commit()
    flash(f'OS aprovada! Cobrança de Sinal gerada (REC). Digite o código REC{os.id} no Caixa para cobrar.')
    return redirect(url_for('luthier_dashboard'))

@app.route('/luthier/finalizar/<int:id>', methods=['POST'])
def luthier_finalizar(id):
    if 'usuario_id' not in session: return redirect(url_for('dashboard'))
    os = OrdemServico.query.get_or_404(id)
    os.status = 'Finalizado'
    
    valor_total = (os.valor_mao_de_obra or 0) + (os.valor_pecas or 0)
    valor_restante = valor_total / 2.0
    
    db.session.add(ContaReceber(
        descricao=f"Pgto Final (50%) OS-{os.id} Luthier ({os.cliente_nome})",
        modulo_origem="Luthier", origem_id=os.id, valor=valor_restante,
        data_vencimento=datetime.utcnow().date(), status="Pendente"
    ))
    
    comissao = (os.valor_mao_de_obra or 0) * 0.40
    if comissao > 0:
        db.session.add(ContaPagar(
            descricao=f"Comissão Luthier {os.luthier_responsavel} (OS-{os.id})",
            valor=comissao, data_vencimento=datetime.utcnow().date(), status="Pendente"
        ))
    
    db.session.commit()
    flash('Serviço concluído! Cobrança final enviada ao cliente e comissão do Luthier gerada.')
    return redirect(url_for('luthier_dashboard'))

@app.route('/luthier/entregar/<int:id>', methods=['POST'])
def luthier_entregar(id):
    if 'usuario_id' not in session: return redirect(url_for('dashboard'))
    os = OrdemServico.query.get_or_404(id)
    os.status = 'Despachado/Entregue'
    db.session.commit()
    flash('Instrumento entregue! A ficha foi movida para o Arquivo Morto no final da página.')
    return redirect(url_for('luthier_dashboard'))

if __name__ == '__main__':
    app.run(debug=True)

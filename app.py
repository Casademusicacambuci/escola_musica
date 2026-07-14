from flask import Flask, render_template, request, redirect, url_for, flash, session, Response, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os
import csv
from io import StringIO

from models import db, Usuario, Aluno, Professor, AgendamentoEstudio, Aula, Fornecedor, Funcionario, ContaReceber, ContaPagar, FluxoCaixa, Produto

app = Flask(__name__)
app.secret_key = 'chave_secreta_cambuci_2026' 
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///cambuci_crm.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

db.init_app(app)

# Banco Blindado
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
# SECRETARIA E PROFESSORES (CORRIGIDOS)
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
            db.session.commit()
            flash('Aluno matriculado com sucesso!')
            return redirect(url_for('gerenciar_alunos'))
    return render_template('alunos.html', alunos=Aluno.query.order_by(Aluno.nome).all())

@app.route('/secretaria/alunos/editar/<int:id>', methods=['POST'])
def editar_aluno(id):
    if 'usuario_id' not in session: return redirect(url_for('dashboard'))
    aluno = Aluno.query.get_or_404(id)
    aluno.nome = request.form.get('nome')
    aluno.email = request.form.get('email')
    aluno.telefone = request.form.get('telefone')
    aluno.curso = request.form.get('curso')
    aluno.nivel = request.form.get('nivel')
    aluno.status = request.form.get('status')
    aluno.endereco_completo = request.form.get('endereco')
    v_mens = request.form.get('valor_mensalidade', '0')
    aluno.valor_mensalidade = float(v_mens.replace(',', '.')) if v_mens else 0.0
    db.session.commit()
    flash('Dados do aluno atualizados com sucesso!')
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
        
        # Correção do Anexo dos Professores
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

# Correção do CSV de Professores que dava Not Found
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

# ==============================================================================
# AGENDA DE AULAS & ESTÚDIOS
# ==============================================================================
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
    aula.aluno_id = request.form.get('aluno_id'); aula.professor_id = request.form.get('professor_id')
    aula.instrumento = request.form.get('instrumento')
    aula.data_aula = datetime.strptime(request.form.get('data_aula'), '%Y-%m-%d').date()
    aula.horario_inicio = datetime.strptime(request.form.get('horario_inicio'), '%H:%M').time()
    aula.horario_final = datetime.strptime(request.form.get('horario_final'), '%H:%M').time()
    aula.status = request.form.get('status'); aula.observacoes = request.form.get('observacoes')
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
        
        # Quando conclui, envia para o financeiro como "Pendente" ou "Pago"
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
    if 'usuario_id' not in session or session.get('role') != 'admin': return redirect(url_for('dashboard'))
    hoje = datetime.utcnow().date()
    contas_receber = ContaReceber.query.order_by(ContaReceber.data_vencimento).all()
    contas_pagar = ContaPagar.query.order_by(ContaPagar.data_vencimento).all()
    total_recebido = sum(c.valor for c in contas_receber if c.status == 'Pago')
    total_a_receber = sum(c.valor for c in contas_receber if c.status == 'Pendente')
    total_pago = sum(c.valor for c in contas_pagar if c.status == 'Pago')
    total_a_pagar = sum(c.valor for c in contas_pagar if c.status == 'Pendente')
    
    inadimplentes = [c for c in contas_receber if c.status == 'Pendente' and c.data_vencimento < hoje]

    repasse_profs = []
    for prof in Professor.query.filter_by(status='Ativo').all():
        aulas_concluidas = Aula.query.filter_by(professor_id=prof.id, status='Concluída').all()
        aulas_mes = [a for a in aulas_concluidas if a.data_aula.month == hoje.month and a.data_aula.year == hoje.year]
        alunos_unicos = list({a.aluno for a in aulas_mes}) 
        valor_mensalidades = sum((aluno.valor_mensalidade or 0.0) for aluno in alunos_unicos)
        if valor_mensalidades > 0:
            repasse_profs.append({'nome': prof.nome, 'qtd_alunos': len(alunos_unicos), 'valor_base': valor_mensalidades, 'comissao': valor_mensalidades * 0.40})

    return render_template('financeiro.html', receber=contas_receber, pagar=contas_pagar, 
                           t_recebido=total_recebido, t_a_receber=total_a_receber, t_pago=total_pago, t_a_pagar=total_a_pagar, saldo=total_recebido - total_pago,
                           inadimplentes=inadimplentes, repasse_profs=repasse_profs, fornecedores=Fornecedor.query.all(), funcionarios=Funcionario.query.all())

@app.route('/financeiro/repasse/pagar', methods=['POST'])
def registrar_repasse():
    if 'usuario_id' not in session: return redirect(url_for('dashboard'))
    nova_despesa = ContaPagar(
        descricao=f"Repasse Prof. {request.form.get('nome_professor')} - Mês {datetime.utcnow().strftime('%m/%Y')}",
        valor=float(request.form.get('valor_comissao', '0')), data_vencimento=datetime.utcnow().date(), status="Pendente"
    )
    db.session.add(nova_despesa)
    db.session.commit()
    flash('Pagamento enviado para a aba Contas a Pagar!')
    return redirect(url_for('financeiro_dashboard'))

@app.route('/financeiro/exportar', methods=['POST'])
def exportar_financeiro():
    if 'usuario_id' not in session: return redirect(url_for('dashboard'))
    d_inicio = datetime.strptime(request.form.get('data_inicio'), '%Y-%m-%d').date()
    d_fim = datetime.strptime(request.form.get('data_fim'), '%Y-%m-%d').date()
    tipo = request.form.get('tipo_relatorio')
    filtro_modulo = request.form.get('filtro_modulo', 'Todos')

    si = StringIO(); cw = csv.writer(si, delimiter=';')
    cw.writerow([f'RELATORIO FINANCEIRO - Periodo: {d_inicio} ate {d_fim}'])
    if filtro_modulo != 'Todos': cw.writerow([f'Filtro Aplicado: {filtro_modulo}'])
    cw.writerow([])
    
    if tipo in ['receitas', 'ambos']:
        cw.writerow(['ENTRADAS', 'Vencimento', 'Pagamento', 'Origem', 'Descricao', 'Valor', 'Status'])
        query_receitas = ContaReceber.query.filter(ContaReceber.data_vencimento >= d_inicio, ContaReceber.data_vencimento <= d_fim)
        if filtro_modulo != 'Todos': query_receitas = query_receitas.filter(ContaReceber.modulo_origem == filtro_modulo)
        for r in query_receitas.order_by(ContaReceber.data_vencimento).all():
            dp = r.data_pagamento.strftime('%d/%m/%Y') if r.data_pagamento else ''
            cw.writerow(['', r.data_vencimento.strftime('%d/%m/%Y'), dp, r.modulo_origem, r.descricao, r.valor, r.status])
            
    if tipo in ['despesas', 'ambos']:
        cw.writerow([]); cw.writerow(['SAIDAS', 'Vencimento', 'Pagamento', 'Descricao', 'Valor', 'Status'])
        if filtro_modulo == 'Todos':
            for d in ContaPagar.query.filter(ContaPagar.data_vencimento >= d_inicio, ContaPagar.data_vencimento <= d_fim).order_by(ContaPagar.data_vencimento).all():
                dp = d.data_pagamento.strftime('%d/%m/%Y') if d.data_pagamento else ''
                cw.writerow(['', d.data_vencimento.strftime('%d/%m/%Y'), dp, d.descricao, d.valor, d.status])

    return Response('\ufeff' + si.getvalue(), mimetype="text/csv; charset=utf-8", headers={"Content-Disposition": "attachment;filename=relatorio.csv"})

@app.route('/financeiro/receber/nova', methods=['POST'])
def nova_conta_receber():
    if 'usuario_id' not in session: return redirect(url_for('dashboard'))
    nova_conta = ContaReceber(
        descricao=request.form.get('descricao'), modulo_origem=request.form.get('modulo_origem', 'Mensalidade'),
        valor=float(request.form.get('valor', '0').replace(',', '.')), data_vencimento=datetime.strptime(request.form.get('data_vencimento'), '%Y-%m-%d').date(), 
        status=request.form.get('status'), data_pagamento=datetime.utcnow().date() if request.form.get('status') == 'Pago' else None
    )
    db.session.add(nova_conta)
    db.session.commit()
    return redirect(url_for('financeiro_dashboard'))

@app.route('/financeiro/pagar/nova', methods=['POST'])
def nova_conta_pagar():
    if 'usuario_id' not in session: return redirect(url_for('dashboard'))
    nova_conta = ContaPagar(
        descricao=request.form.get('descricao'), fornecedor_id=request.form.get('fornecedor_id') or None,
        valor=float(request.form.get('valor', '0').replace(',', '.')), data_vencimento=datetime.strptime(request.form.get('data_vencimento'), '%Y-%m-%d').date(), 
        status=request.form.get('status'), data_pagamento=datetime.utcnow().date() if request.form.get('status') == 'Pago' else None
    )
    db.session.add(nova_conta)
    db.session.commit()
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
        preco_custo=float(request.form.get('preco_custo').replace(',', '.')), preco_venda=float(request.form.get('preco_venda').replace(',', '.')),
        quantidade_estoque=int(request.form.get('quantidade_estoque', '0'))
    )
    db.session.add(novo_prod)
    db.session.commit()
    return redirect(url_for('gerenciar_estoque'))

@app.route('/estoque/excluir/<int:id>', methods=['POST'])
def excluir_produto(id):
    if 'usuario_id' not in session: return redirect(url_for('dashboard'))
    db.session.delete(Produto.query.get_or_404(id))
    db.session.commit()
    return redirect(url_for('gerenciar_estoque'))

# ==============================================================================
# CAIXA PDV: A MÁGICA DA CONEXÃO "REC-"
# ==============================================================================
@app.route('/caixa', methods=['GET'])
def caixa_pdv():
    if 'usuario_id' not in session: return redirect(url_for('dashboard'))
    return render_template('caixa.html')

@app.route('/api/produto/<codigo>')
def api_buscar_produto(codigo):
    if 'usuario_id' not in session: return jsonify({'erro': 'Não autorizado'})
    codigo = codigo.strip().upper()
    
    # 1. Se o código for um recebimento pendente (Ex: REC-12)
    if codigo.startswith('REC-'):
        try:
            conta_id = int(codigo.split('-')[1])
            conta = ContaReceber.query.get(conta_id)
            if conta:
                if conta.status == 'Pago':
                    return jsonify({'erro': 'Esta cobrança já consta como PAGA no Financeiro!'})
                return jsonify({
                    'id': f'REC-{conta.id}', 
                    'nome': f"PAGAMENTO: {conta.modulo_origem} ({conta.descricao})", 
                    'preco': conta.valor, 'tipo': 'receita'
                })
        except:
            pass # Cai para o erro genérico no final

    # 2. Se for um produto normal
    produto = Produto.query.filter_by(codigo_barras=codigo).first()
    if produto:
        if produto.quantidade_estoque <= 0:
            return jsonify({'erro': f'Produto "{produto.nome}" sem estoque!'})
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
        if item_id.startswith('REC-'):
            # Conexão: Marca a cobrança do estúdio/mensalidade como PAGA no financeiro!
            conta_id = int(item_id.split('-')[1])
            conta = ContaReceber.query.get(conta_id)
            if conta:
                conta.status = 'Pago'
                conta.data_pagamento = datetime.utcnow().date()
                conta.forma_pagamento = forma_pagamento
        else:
            # Produto físico: dá baixa no estoque
            produto = Produto.query.get(item['id'])
            if produto:
                produto.quantidade_estoque -= item['quantidade']
                produtos_fisicos.append(f"{item['quantidade']}x {produto.nome}")
                
    # Cria uma receita no financeiro SÓ para os salgados/águas/loja
    if produtos_fisicos:
        total_produtos = sum(float(i['preco']) * int(i['quantidade']) for i in itens if not str(i['id']).startswith('REC-'))
        if total_produtos > 0:
            nova_venda = ContaReceber(
                descricao="Venda PDV: " + ", ".join(produtos_fisicos), modulo_origem="Loja / PDV", valor=total_produtos,
                data_vencimento=datetime.utcnow().date(), data_pagamento=datetime.utcnow().date(),
                status="Pago", forma_pagamento=forma_pagamento
            )
            db.session.add(nova_venda)
            
    db.session.commit()
    return jsonify({'sucesso': True})

@app.route('/caixa/fechamento', methods=['GET'])
def fechamento_caixa():
    if 'usuario_id' not in session: return jsonify({'erro': 'Não autorizado'})
    hoje = datetime.utcnow().date()
    recebimentos_hoje = ContaReceber.query.filter_by(data_pagamento=hoje, status='Pago').all()
    resumo = {'Dinheiro': 0.0, 'Pix': 0.0, 'Cartao_Credito': 0.0, 'Cartao_Debito': 0.0, 'Total': 0.0}
    for r in recebimentos_hoje:
        forma = r.forma_pagamento
        if forma == 'Pix': resumo['Pix'] += r.valor
        elif forma == 'Cartão de Crédito': resumo['Cartao_Credito'] += r.valor
        elif forma == 'Cartão de Débito': resumo['Cartao_Debito'] += r.valor
        else: resumo['Dinheiro'] += r.valor 
        resumo['Total'] += r.valor
    return jsonify(resumo)

if __name__ == '__main__':
    app.run(debug=True)

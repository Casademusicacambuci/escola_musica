# Certifique-se de que a rota de atualização de status esteja exatamente assim:

@app.route('/atualizar_status_agenda/<int:id>/<string:novo_status>')
def atualizar_status_agenda(id, novo_status):
    conn = get_db_connection()
    compromisso = conn.execute('SELECT * FROM agenda WHERE id = ?', (id,)).fetchone()
    
    if compromisso:
        status_anterior = compromisso['status']
        
        # Se for marcado como Pago OU Concluído vindo de "A pagar", lança no financeiro
        if novo_status in ['Pago', 'Concluído'] and status_anterior == 'A pagar' and compromisso['valor_reserva'] > 0:
            descricao_financeiro = f"Pgto Recebido ({novo_status}) - {compromisso['tipo_agendamento']} - Cli: {compromisso['nome_responsavel']}"
            conn.execute('''
                INSERT INTO financeiro (tipo, categoria_fluxo, descricao, valor, data)
                VALUES (?, ?, ?, ?, ?)
            ''', ('entrada', 'Estúdios', descricao_financeiro, compromisso['valor_reserva'], datetime.now().strftime('%Y-%m-%d %H:%M')))
            
        conn.execute('UPDATE agenda SET status = ? WHERE id = ?', (novo_status, id))
        conn.commit()
        
    conn.close()
    return redirect(url_for('index'))

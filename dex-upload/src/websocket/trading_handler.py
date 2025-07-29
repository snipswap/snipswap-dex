def register_trading_events(socketio):
    """Register trading WebSocket events"""
    
    @socketio.on('connect')
    def handle_connect():
        print('Trading WebSocket connected')
    
    @socketio.on('disconnect') 
    def handle_disconnect():
        print('Trading WebSocket disconnected')


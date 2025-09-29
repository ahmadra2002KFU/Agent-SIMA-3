"""
Test send button functionality via WebSocket
"""
import asyncio
import json
import websockets

async def test_send_button():
    """Test WebSocket connection and message sending."""
    uri = "ws://localhost:8010/ws"
    
    try:
        print("🔌 Connecting to WebSocket on port 8010...")
        async with websockets.connect(uri) as websocket:
            print("✅ Connected to WebSocket successfully")
            
            # Send test query
            test_query = {"message": "How many Saudi patients are there"}
            print(f"📤 Sending query: {test_query}")
            
            await websocket.send(json.dumps(test_query))
            print("✅ Query sent successfully")
            
            # Listen for responses
            timeout_count = 0
            max_timeout = 30
            
            while timeout_count < max_timeout:
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                    data = json.loads(response)
                    print(f"📥 Received: {data.get('event', 'unknown')} - {data.get('field', '')}")
                    
                    if data.get("event") == "end":
                        print("🏁 Response complete!")
                        print("✅ Send button functionality test: SUCCESS")
                        return True
                        
                except asyncio.TimeoutError:
                    timeout_count += 1
                    if timeout_count % 5 == 0:
                        print(f"⏳ Waiting... ({timeout_count}/{max_timeout})")
                    continue
                    
            print("⏰ Timeout reached")
            return False
            
    except Exception as e:
        print(f"❌ WebSocket connection failed: {e}")
        return False

if __name__ == "__main__":
    result = asyncio.run(test_send_button())
    if result:
        print("\n🎉 Send button functionality is working correctly!")
    else:
        print("\n❌ Send button functionality test failed")


from pyngrok import ngrok, conf

# 1. Point to your manually downloaded ngrok.exe
conf.get_default().ngrok_path = r"C:\Users\Mafaa\Downloads\ngrok-v3-stable-windows-amd64\ngrok.exe"  # ← your actual path

# 2. Authenticate with your token
ngrok.set_auth_token("2wMigr6YupZ0QHLqq2SbYvPDs1p_3nDox7z6nFyuUQdLUCcvA")         

# 3. Open an HTTPS tunnel on port 8000
public_url = ngrok.connect(8000, bind_tls=True)          
print(" * ngrok tunnel:", public_url)

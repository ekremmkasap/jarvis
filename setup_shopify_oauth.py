"""
Add Shopify OAuth callback handler to bridge.py
and deploy the product sync skill.
"""
import paramiko, time, json

host, username, password = "192.168.1.109", "userk", "userk1"

CLIENT_ID = "658472d581c8894deb450f7f6f9de137"
CLIENT_SECRET = "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"
SHOP = "vn3i8c-ks.myshopify.com"
REDIRECT_URI = "http://192.168.1.109:8080/auth/callback"
SCOPES = "read_products,read_inventory,read_orders,read_price_rules"

# OAuth handler code to add to bridge.py WebHandler
OAUTH_HANDLER = '''
    def _handle_shopify_oauth(self):
        """Handle Shopify OAuth callback"""
        from urllib.parse import urlparse, parse_qs
        from urllib.request import urlopen, Request
        import json
        
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        code = params.get("code", [""])[0]
        shop = params.get("shop", [""])[0]
        
        if not code or not shop:
            self._json({"error": "Missing code or shop"}, 400)
            return
        
        # Exchange code for token
        payload = json.dumps({
            "client_id": "658472d581c8894deb450f7f6f9de137",
            "client_secret": "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",
            "code": code
        }).encode()
        
        try:
            req = Request(
                f"https://{shop}/admin/oauth/access_token",
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urlopen(req, timeout=15) as resp:
                token_data = json.loads(resp.read())
                token = token_data.get("access_token", "")
            
            # Save token
            with open("/opt/jarvis/shopify_token.txt", "w") as f:
                f.write(f"SHOP={shop}\\nTOKEN={token}\\n")
            
            log.info(f"Shopify OAuth complete! Token: {token[:20]}...")
            
            # Send HTML response
            html = f"""<html><body style="background:#0a0a0f;color:#00ff88;font-family:sans-serif;text-align:center;padding:50px">
            <h1>✅ Jarvis Shopify Bağlantısı Tamam!</h1>
            <p>Token alındı ve kaydedildi.</p>
            <p>Şimdi ürünler çekiliyor...</p>
            </body></html>"""
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(html.encode())
            
            # Trigger product sync in background
            import threading
            threading.Thread(target=_sync_shopify_products, args=(shop, token), daemon=True).start()
            
        except Exception as e:
            log.error(f"OAuth error: {e}")
            self._json({"error": str(e)}, 500)
'''

# Product sync function to add
SYNC_FUNCTION = '''
def _sync_shopify_products(shop, token):
    """Sync all products from Shopify store"""
    import json, time
    from urllib.request import urlopen, Request
    
    log.info(f"Shopify urun sync basliyor: {shop}")
    all_products = []
    page_info = None
    
    while True:
        url = f"https://{shop}/admin/api/2024-01/products.json?limit=250"
        if page_info:
            url += f"&page_info={page_info}"
        
        try:
            req = Request(url, headers={
                "X-Shopify-Access-Token": token,
                "Content-Type": "application/json"
            })
            with urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read())
                products = data.get("products", [])
                all_products.extend(products)
                log.info(f"  Sayfa: {len(all_products)} urun")
                
                # Check for pagination
                link_header = resp.headers.get("Link", "")
                if "rel=\\"next\\"" in link_header:
                    import re
                    m = re.search(r'page_info=([^&>]+)', link_header.split("rel=\\"next\\"")[0])
                    page_info = m.group(1) if m else None
                else:
                    break
                time.sleep(0.5)
        except Exception as e:
            log.error(f"Sync error: {e}")
            break
    
    # Save knowledge file
    lines = [f"# Shopify Mağaza: {shop}", f"# Toplam: {len(all_products)} urun", ""]
    
    vendors = list(set(p.get("vendor","") for p in all_products if p.get("vendor")))
    types = list(set(p.get("product_type","") for p in all_products if p.get("product_type")))
    
    lines.append(f"## Ozet")
    lines.append(f"- Toplam Urun: {len(all_products)}")
    lines.append(f"- Kategoriler: {', '.join(types[:10]) or '-'}")
    lines.append(f"- Tedarikciler: {', '.join(vendors[:10]) or '-'}")
    lines.append("")
    lines.append("## Urunler")
    
    for p in all_products:
        variants = p.get("variants", [])
        prices = [float(v.get("price",0)) for v in variants if v.get("price")]
        min_p = min(prices) if prices else 0
        max_p = max(prices) if prices else 0
        stock = sum(v.get("inventory_quantity",0) for v in variants)
        price_str = f"${min_p:.2f}" if min_p==max_p else f"${min_p:.2f}-${max_p:.2f}"
        
        lines.append(f"- **{p.get('title','-')}** | {price_str} | Stok:{stock} | {p.get('product_type','-')}")
    
    knowledge = "\\n".join(lines)
    with open("/opt/jarvis/knowledge/shopify_store.md", "w") as f:
        f.write(knowledge)
    
    # Reload knowledge
    global KNOWLEDGE
    KNOWLEDGE["shopify_store"] = knowledge
    log.info(f"✅ Shopify sync tamamlandi: {len(all_products)} urun")
'''

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(hostname=host, username=username, password=password, timeout=10)

sftp = client.open_sftp()

# Read bridge.py
with sftp.file("/opt/jarvis/openclaw/bridge.py", "r") as f:
    content = f.read().decode()

# Add sync function before main()
if "_sync_shopify_products" not in content:
    content = content.replace(
        "\ndef start_web():",
        SYNC_FUNCTION + "\ndef start_web():"
    )
    print("  ✅ Sync function added")

# Add OAuth route to do_GET
if "shopify_oauth" not in content:
    old = """        elif self.path == "/api/status":"""
    new = """        elif self.path.startswith("/auth/callback"):
            self._handle_shopify_oauth()
            return
        elif self.path == "/api/status":"""
    content = content.replace(old, new)
    
    # Add method to WebHandler class
    old2 = """    def _json(self, data, code=200):"""
    new2 = OAUTH_HANDLER + "\n    def _json(self, data, code=200):"
    content = content.replace(old2, new2)
    print("  ✅ OAuth handler added")

# Write back
with sftp.file("/opt/jarvis/openclaw/bridge.py", "w") as f:
    f.write(content)
sftp.close()

# Syntax check
_, sy, _ = client.exec_command("python3 -m py_compile /opt/jarvis/openclaw/bridge.py && echo SYNTAX_OK 2>&1", get_pty=True)
sy_out = sy.read().decode().strip()
print(f"  Syntax: {sy_out}")

if "SYNTAX_OK" in sy_out:
    client.exec_command("echo 'userk1' | sudo -S systemctl restart jarvis.service")
    time.sleep(4)
    _, st, _ = client.exec_command("systemctl is-active jarvis.service")
    print(f"  Service: {st.read().decode().strip()}")
else:
    print("  ❌ SYNTAX ERROR")
    _, err, _ = client.exec_command("python3 /opt/jarvis/openclaw/bridge.py 2>&1 | head -20")
    print(err.read().decode())

client.close()

# Print the install URL for the user
import urllib.parse
params = urllib.parse.urlencode({
    "client_id": CLIENT_ID,
    "scope": SCOPES,
    "redirect_uri": REDIRECT_URI,
    "state": "jarvis2024"
})
install_url = f"https://{SHOP}/admin/oauth/authorize?{params}"
print(f"\n✅ Install URL:")
print(install_url)
print("\nBu URL'yi tarayıcında aç → Onayla → Token otomatik kaydedilir!")

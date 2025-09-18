# app.py
import os
import hashlib
import uuid
from datetime import datetime
from flask import Flask, render_template, jsonify, request, send_file, abort, url_for
import qrcode
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm

# try to import psutil; if not available or fails, we'll return demo drives
try:
    import psutil
except Exception:
    psutil = None

app = Flask(__name__, template_folder="templates", static_folder="static")

CERT_DIR = "certificates"
os.makedirs(CERT_DIR, exist_ok=True)

# in-memory record of certificates (demo)
wipe_history = {}

def list_system_drives():
    """Return list of detected drives or demo list if psutil unavailable."""
    if psutil:
        try:
            parts = psutil.disk_partitions(all=False)
            return [p.device for p in parts]
        except Exception:
            pass
    # fallback demo drives (safe)
    return ["C:\\", "D:\\"]

def _make_qr_image(url, out_path):
    qr = qrcode.QRCode(box_size=6, border=2)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image()
    img.save(out_path)

def generate_pdf_certificate(cert_id, drive_name, pre_hash, post_hash):
    """Create PDF certificate with QR code and third-party verification info."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    pdf_path = os.path.join(CERT_DIR, f"erasex_cert_{cert_id}.pdf")
    qr_path = os.path.join(CERT_DIR, f"qr_{cert_id}.png")

    # verify_url - use external URL (Render will provide domain)
    verify_url = url_for("verify", cert_id=cert_id, _external=True)
    _make_qr_image(verify_url, qr_path)

    width, height = A4
    c = canvas.Canvas(pdf_path, pagesize=A4)

    # Title
    c.setFont("Helvetica-Bold", 20)
    c.drawCentredString(width / 2, height - 30 * mm, "EraseX Secure Wipe Certificate")

    # Left column (details)
    c.setFont("Helvetica", 11)
    left_x = 25 * mm
    y = height - 50 * mm
    line_height = 14
    c.drawString(left_x, y, f"Certificate ID: {cert_id}")
    c.drawString(left_x, y - line_height, f"Drive (simulated): {drive_name}")
    c.drawString(left_x, y - 2 * line_height, f"Generated: {timestamp}")
    c.drawString(left_x, y - 3 * line_height, f"Pre-wipe hash: {pre_hash}")
    c.drawString(left_x, y - 4 * line_height, f"Post-wipe hash: {post_hash}")

    # QR top-right
    qr_w = 50 * mm
    qr_x = width - qr_w - 25 * mm
    qr_y = height - qr_w - 40 * mm
    try:
        c.drawImage(qr_path, qr_x, qr_y, width=qr_w, height=qr_w)
    except Exception:
        pass

    # Verification section (below details)
    section_y = y - 6 * line_height
    c.setFont("Helvetica-Bold", 12)
    c.drawString(left_x, section_y, "Third-Party Verification:")
    c.setFont("Helvetica-Oblique", 10)
    c.drawString(left_x, section_y - 15, "Scan the QR code or visit:")
    c.setFillColorRGB(0, 0, 1)
    c.drawString(left_x, section_y - 30, verify_url)
    c.setFillColorRGB(0, 0, 0)

    # Footer
    c.setFont("Helvetica-Oblique", 9)
    c.drawCentredString(width / 2, 15 * mm,
                        "This certificate was generated in DEMO mode. No physical drives were modified.")

    c.showPage()
    c.save()

    # cleanup qr file
    try:
        os.remove(qr_path)
    except Exception:
        pass

    return pdf_path

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/list-drives")
def api_list_drives():
    drives = list_system_drives()
    return jsonify({"drives": drives})

@app.route("/wipe-drive", methods=["POST"])
def api_wipe_drive():
    data = request.get_json(force=True)
    drive = data.get("drive")
    if not drive:
        return jsonify({"error": "Please specify 'drive'"}), 400

    # Simulated wipe hashes
    demo_bytes = b"DemoSensitiveDataForHashing"
    pre_hash = hashlib.sha256(demo_bytes).hexdigest()
    post_hash = hashlib.sha256(b"\x00" * len(demo_bytes)).hexdigest()

    cert_id = str(uuid.uuid4())[:8]
    pdf_path = generate_pdf_certificate(cert_id, drive, pre_hash, post_hash)

    wipe_history[cert_id] = {
        "drive": drive,
        "pre_hash": pre_hash,
        "post_hash": post_hash,
        "timestamp": datetime.now().isoformat(),
        "file": pdf_path,
    }

    return jsonify({
        "drive": drive,
        "pre_hash": pre_hash,
        "post_hash": post_hash,
        "certificate_id": cert_id,
        "download_url": f"/download/{cert_id}"
    })

@app.route("/download/<cert_id>")
def download_certificate(cert_id):
    rec = wipe_history.get(cert_id)
    if not rec:
        return abort(404, "Certificate not found")
    return send_file(rec["file"], as_attachment=True)

@app.route("/verify/<cert_id>")
def verify(cert_id):
    rec = wipe_history.get(cert_id)
    if not rec:
        return f"<h2>Certificate {cert_id} not found</h2>", 404
    return f"""
    <html><head><title>Verify {cert_id}</title></head>
    <body style="font-family:Arial,Helvetica,sans-serif;padding:20px;">
      <h1>✅ EraseX Certificate Verified</h1>
      <p><strong>Certificate ID:</strong> {cert_id}</p>
      <p><strong>Drive:</strong> {rec['drive']}</p>
      <p><strong>Timestamp:</strong> {rec['timestamp']}</p>
      <p><strong>Pre-wipe hash:</strong> {rec['pre_hash']}</p>
      <p><strong>Post-wipe hash:</strong> {rec['post_hash']}</p>
      <p>Status: <strong>SUCCESS (Simulated)</strong></p>
    </body></html>
    """

if __name__ == "__main__":
    # locally you can still run python app.py
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)



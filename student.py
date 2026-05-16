import numpy as np, sounddevice as sd, requests, cv2, sys, pyotp
from pyzbar.pyzbar import decode

# --- Configuration ---
BASE_URL = "http://127.0.0.1:5000"
SECRET_KEY = "SUPERSECRETBASE32KEY"
TARGET_FREQ, FS, DURATION = 18000, 44100, 5
totp = pyotp.TOTP(SECRET_KEY, interval=30)
TARGET_BAND = (17500, 18500)

def login_student():
    print("=== Student Attendance Login ===")
    username, password = input("Username: "), input("Password: ")
    try:
        resp = requests.post(f"{BASE_URL}/login", json={"username": username, "password": password})
        if resp.status_code == 200:
            data = resp.json()
            print(f"✅ Welcome, {data['name']}.")
            return data['user_id']
        print(f"❌ Login Failed: {resp.json().get('message')}")
    except Exception as e:
        print(f"❌ Connection Error: {e}")
    return None

def detect_sound():
    print(f"\nListening for teacher's signal...")
    try:
        recording = sd.rec(int(DURATION * FS), samplerate=FS, channels=1, dtype="float32")
        sd.wait()
        sig = recording.flatten()
        if np.max(np.abs(sig)) < 0.001:
            return False

        sig = sig / (np.max(np.abs(sig)) + 1e-9)
        windowed = sig * np.hanning(len(sig))
        fft_data = np.abs(np.fft.rfft(windowed))
        freqs = np.fft.rfftfreq(len(windowed), 1/FS)

        band_mask = (freqs >= TARGET_BAND[0]) & (freqs <= TARGET_BAND[1])
        signal_band = fft_data[band_mask]
        if signal_band.size == 0:
            return False

        target_peak = np.max(signal_band)
        target_freq = freqs[band_mask][np.argmax(signal_band)]

        lower_band = fft_data[(freqs >= 15000) & (freqs < TARGET_BAND[0])]
        upper_band = fft_data[(freqs > TARGET_BAND[1]) & (freqs <= 20000)]
        noise_floor = np.mean(np.concatenate([lower_band, upper_band])) if lower_band.size or upper_band.size else 1e-9
        snr = target_peak / (noise_floor + 1e-9)

        print(f"Peak: {target_freq:.2f}Hz | SNR: {snr:.2f}")
        return snr > 2.5
    except: return False

def scan_qr():
    cap = cv2.VideoCapture(0)
    while True:
        ret, frame = cap.read()
        if not ret: break
        for qr in decode(frame):
            token = qr.data.decode('utf-8')
            cap.release()
            cv2.destroyAllWindows()
            return token
        cv2.imshow("Scan QR", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'): break
    cap.release()
    cv2.destroyAllWindows()
    return None

if __name__ == "__main__":
    uid = login_student()
    if not uid: sys.exit()

    method, token = "sound", None
    if detect_sound():
        print("✅ Sound Verified!")
        token = totp.now()
    else:
        print("❌ Sound failed. Try QR.")
        method, token = "qr_backup", scan_qr()

    if token:
        resp = requests.post(f"{BASE_URL}/mark_present", json={"user_id": uid, "method": method, "token": token})
        print(f"Result: {resp.json()['message']}")
import io, json, pathlib
import numpy as np
import pandas as pd
import cv2
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
from sklearn.model_selection import train_test_split
from tqdm import tqdm

from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

# ──────────────── CONFIGURATION ────────────────
CSV_PATH = 'FFHQ_metadata.csv'
MAPPING_JSON = 'mapping.json'
DATA_FOLDER_ID = '1aY-x69okHHCAsPOESe4HH54zb3eQLDPB'
BATCH_SIZE = 32
EPOCHS = 10
LR = 2e-4
DEVICE = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
MODEL_OUT = 'FFHQ_age_progression.pth'
MAX_SAMPLES = 20000  # cap dataset size for faster training


def authenticate_drive_api():
    print("[INFO] Authenticating with Google Drive API...")
    scopes = ['https://www.googleapis.com/auth/drive.readonly']
    flow = InstalledAppFlow.from_client_secrets_file('client_oauth.json', scopes)
    creds = flow.run_local_server(port=0)
    return build('drive', 'v3', credentials=creds)


def parse_age_group(s: str) -> float:
    """Convert '0-2' → 1.0, '20-29' → 24.5, etc."""
    parts = s.split('-')
    return (int(parts[0]) + int(parts[1])) / 2 if len(parts) == 2 else float(parts[0])


class FFHQAgingDataset(Dataset):
    """PyTorch Dataset reading images directly from Drive."""

    def __init__(self, drive_service, ids, ages):
        self.drive = drive_service
        self.ids = ids
        self.ages = ages

    def __len__(self):
        return len(self.ids)

    def __getitem__(self, idx):
        file_id = self.ids[idx]
        request = self.drive.files().get_media(fileId=file_id)
        buffer = io.BytesIO()
        downloader = MediaIoBaseDownload(buffer, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()
        buffer.seek(0)

        img = cv2.imdecode(np.frombuffer(buffer.read(), np.uint8), cv2.IMREAD_COLOR)
        img = cv2.resize(img, (256, 256)).astype(np.float32) / 255.0
        img = torch.from_numpy(img).permute(2, 0, 1)  # C,H,W
        return img, torch.tensor(self.ages[idx], dtype=torch.float32)


class AgeProgressionModel(nn.Module):
    """Simple encoder–age–decoder network."""

    def __init__(self):
        super().__init__()
        self.encoder = nn.Sequential(
            nn.Conv2d(3, 64, 4, 2, 1), nn.ReLU(),
            nn.Conv2d(64, 128, 4, 2, 1), nn.ReLU(),
            nn.Conv2d(128, 256, 4, 2, 1), nn.ReLU(),
            nn.Flatten(),
            nn.Linear(256 * 32 * 32, 512), nn.ReLU()
        )
        self.mapping = nn.Sequential(
            nn.Linear(1, 128), nn.ReLU(),
            nn.Linear(128, 512), nn.ReLU()
        )
        self.decoder = nn.Sequential(
            nn.Linear(512 * 2, 256 * 32 * 32), nn.ReLU(),
            nn.Unflatten(1, (256, 32, 32)),
            nn.ConvTranspose2d(256, 128, 4, 2, 1), nn.ReLU(),
            nn.ConvTranspose2d(128, 64, 4, 2, 1), nn.ReLU(),
            nn.ConvTranspose2d(64, 3, 4, 2, 1), nn.Sigmoid()
        )

    def forward(self, x, age):
        z_id = self.encoder(x)
        z_age = self.mapping(age.unsqueeze(1))
        return self.decoder(torch.cat([z_id, z_age], dim=1))


def train(train_loader, test_loader):
    model = AgeProgressionModel().to(DEVICE)
    criterion = nn.MSELoss()
    optimizer = optim.Adam(model.parameters(), lr=LR, betas=(0.5, 0.999))

    for epoch in range(1, EPOCHS + 1):
        model.train()
        total_loss = 0
        for images, ages in tqdm(train_loader, desc=f"Epoch {epoch}", unit="batch"):
            images, ages = images.to(DEVICE), ages.to(DEVICE)
            optimizer.zero_grad()

            # Normal training without mixed precision
            out = model(images, ages)
            pred = out.mean((1, 2, 3))
            loss = criterion(pred, ages)

            loss.backward()
            optimizer.step()
            total_loss += loss.item() * images.size(0)

        print(f"Epoch {epoch}/{EPOCHS} — Train MSE: {total_loss / len(train_loader.dataset):.4f}")

    # evaluation
    model.eval()
    test_loss = 0
    with torch.no_grad():
        for images, ages in test_loader:
            images, ages = images.to(DEVICE), ages.to(DEVICE)
            out = model(images, ages)
            pred = out.mean((1, 2, 3))
            test_loss += criterion(pred, ages).item() * images.size(0)
    print(f"[INFO] Test MSE: {test_loss / len(test_loader.dataset):.4f}")

    torch.save(model.state_dict(), MODEL_OUT)
    print(f"[INFO] Saved model to {MODEL_OUT}")


if __name__ == '__main__':
    # 1) Authenticate once
    drive_service = authenticate_drive_api()

    # 2) Load metadata CSV
    print("[INFO] Loading metadata...")
    df = pd.read_csv(CSV_PATH)
    df['age'] = df['age_group'].apply(parse_age_group)

    # 3) Build (or load) mapping.json
    if not pathlib.Path(MAPPING_JSON).is_file():
        print("[INFO] Scanning Drive folder for images…")
        mapping = {}
        token = None
        while True:
            resp = drive_service.files().list(
                q=f"'{DATA_FOLDER_ID}' in parents and mimeType='image/png'",
                fields="nextPageToken, files(id,name)",
                pageSize=1000, pageToken=token
            ).execute()
            for f in resp['files']:
                mapping[f['name'].split('.')[0]] = f['id']
            token = resp.get('nextPageToken')
            if not token:
                break
        with open(MAPPING_JSON, 'w') as fp:
            json.dump(mapping, fp)
    else:
        mapping = json.load(open(MAPPING_JSON))

    # 4) Prepare id→age lists
    ids, ages = [], []
    for _, row in df.iterrows():
        fid = mapping.get(str(int(row['image_number'])))
        if fid:
            ids.append(fid)
            ages.append(row['age'])
    ages = np.array(ages, dtype=np.float32)
    print(f"[INFO] Found {len(ids)} images; subsampling to {MAX_SAMPLES}…")
    if len(ids) > MAX_SAMPLES:
        idxs = np.random.RandomState(42).choice(len(ids), MAX_SAMPLES, replace=False)
        ids = [ids[i] for i in idxs]
        ages = ages[idxs]

    # 5) Split & DataLoaders
    train_ids, test_ids, train_ages, test_ages = train_test_split(ids, ages, test_size=0.2, random_state=42)
    train_ds = FFHQAgingDataset(drive_service, train_ids, train_ages)
    test_ds = FFHQAgingDataset(drive_service, test_ids, test_ages)
    train_loader = DataLoader(train_ds, batch_size=BATCH_SIZE, shuffle=True, num_workers=2)
    test_loader = DataLoader(test_ds, batch_size=BATCH_SIZE, shuffle=False, num_workers=2)

    # 6) Train & evaluate
    train(train_loader, test_loader)

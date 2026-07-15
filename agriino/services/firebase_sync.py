import logging
from datetime import datetime, timezone
from django.conf import settings
from django.db import transaction
import firebase_admin
from firebase_admin import credentials, firestore
from agriino.models import Device, DeviceData

logger = logging.getLogger(__name__)

def sync_firebase_to_db():
    """
    Syncs devices and sensor readings from Firebase Firestore 'agriino_leaf_scans' collection
    to the Django local SQLite database.
    """
    # 1. Check if Firebase credentials path is configured
    cred_path = getattr(settings, 'FIREBASE_CREDENTIALS_PATH', None)
    if not cred_path:
        raise ValueError("Firebase credentials path (FIREBASE_CREDENTIALS_PATH) is not configured in settings.py")
    
    # 2. Initialize Firebase App if not already initialized
    if not firebase_admin._apps:
        logger.info(f"Initializing Firebase Admin with certificate: {cred_path}")
        cred = credentials.Certificate(cred_path)
        firebase_admin.initialize_app(cred)
        logger.info("Firebase Admin SDK initialized successfully.")
    
    db = firestore.client()
    
    # 3. Fetch all documents from the 'agriino_leaf_scans' collection
    logger.info("Fetching documents from 'agriino_leaf_scans' collection...")
    scans_ref = db.collection('agriino_leaf_scans')
    docs = list(scans_ref.stream())
    
    devices_created = 0
    devices_updated = 0
    data_points_created = 0
    
    # Run in transaction to ensure consistency
    with transaction.atomic():
        for doc in docs:
            data = doc.to_dict()
            device_id = doc.id
            
            # Extract coordinates
            lat = data.get('lat')
            lng = data.get('lng')
            if lat is None or lng is None:
                logger.warning(f"Leaf scan document {device_id} is missing coordinates. Skipping.")
                continue
                
            # Create or update Device
            device, created = Device.objects.update_or_create(
                device_id=device_id,
                defaults={
                    'name': f"Leaf Scan {device_id[:6]}",
                    'latitude': float(lat),
                    'longitude': float(lng),
                    'is_active': True
                }
            )
            
            if created:
                devices_created += 1
            else:
                devices_updated += 1
                
            # Extract timestamp from Firestore
            firebase_timestamp = data.get('timestamp')
            
            # Check if this data point already exists for this device to prevent duplicate entries
            data_point_exists = DeviceData.objects.filter(
                device=device,
                firebase_timestamp=firebase_timestamp
            ).exists()
            
            if not data_point_exists:
                # Extract RGB values and other metrics
                avg_data = data.get('avg', {}) or {}
                
                # Helper to float or None
                def to_float(val):
                    if val is None:
                        return None
                    try:
                        return float(val)
                    except (ValueError, TypeError):
                        return None
                
                DeviceData.objects.create(
                    device=device,
                    nitrogen=to_float(data.get('nitrogen', 0)),
                    spad=to_float(data.get('spad')),
                    
                    # Store RGB from root or fallback to avg
                    a_rgb=to_float(data.get('A_RGB', avg_data.get('A_RGB'))),
                    a_r=to_float(data.get('A_R', avg_data.get('A_R'))),
                    a_g=to_float(data.get('A_G', avg_data.get('A_G'))),
                    a_b=to_float(data.get('A_B', avg_data.get('A_B'))),
                    
                    r=to_float(data.get('R', avg_data.get('R'))),
                    g=to_float(data.get('G', avg_data.get('G'))),
                    b=to_float(data.get('B', avg_data.get('B'))),
                    o=to_float(data.get('O', avg_data.get('O'))),
                    v=to_float(data.get('V', avg_data.get('V'))),
                    y=to_float(data.get('Y', avg_data.get('Y'))),
                    
                    t_r=to_float(data.get('T_R', avg_data.get('T_R'))),
                    t_g=to_float(data.get('T_G', avg_data.get('T_G'))),
                    t_b=to_float(data.get('T_B', avg_data.get('T_B'))),
                    
                    eq1=to_float(data.get('eq1')),
                    eq2=to_float(data.get('eq2')),
                    class_eq1=data.get('class_eq1'),
                    class_eq2=data.get('class_eq2'),
                    
                    firebase_timestamp=firebase_timestamp
                )
                data_points_created += 1

        # 4. Fetch all documents from 'agriino_measurements' collection
        logger.info("Fetching documents from 'agriino_measurements' collection...")
        meas_ref = db.collection('agriino_measurements')
        meas_docs = list(meas_ref.stream())
        
        # Create or update placeholder Agriino device
        hist_device, hist_created = Device.objects.update_or_create(
            device_id="Agriino",
            defaults={
                'name': "Agriino Scan History",
                'latitude': -8.1653927,
                'longitude': 113.7176052,
                'is_active': False  # Set to False so it does not render active pins on Kriging map
            }
        )
        
        # Helper to float or None
        def to_float(val):
            if val is None:
                return None
            try:
                return float(val)
            except (ValueError, TypeError):
                return None

        for doc in meas_docs:
            data = doc.to_dict()
            
            # Extract timestamp
            try:
                firebase_timestamp = int(doc.id)
            except (ValueError, TypeError):
                # Fallback to parsing ISO timestamp string if doc.id is not a number
                ts_str = data.get('timestamp')
                if ts_str:
                    try:
                        if '.' in ts_str:
                            base, frac = ts_str.split('.')
                            frac = (frac + "000000")[:6]
                            ts_str_clean = f"{base}.{frac}"
                            dt = datetime.strptime(ts_str_clean, "%Y-%m-%dT%H:%M:%S.%f")
                        else:
                            dt = datetime.strptime(ts_str, "%Y-%m-%dT%H:%M:%S")
                        dt = dt.replace(tzinfo=timezone.utc)
                        firebase_timestamp = int(dt.timestamp() * 1000)
                    except Exception:
                        firebase_timestamp = None
                else:
                    firebase_timestamp = None
                    
            if not firebase_timestamp:
                continue
                
            # Check if this data point already exists for this placeholder device
            data_point_exists = DeviceData.objects.filter(
                device=hist_device,
                firebase_timestamp=firebase_timestamp
            ).exists()
            
            if not data_point_exists:
                # Extract SPAD value
                spad = to_float(data.get('spad_value', data.get('value')))
                if spad is None:
                    avg_data = data.get('avg_data', {}) or {}
                    spad = to_float(avg_data.get('spad'))
                    
                if spad is None:
                    continue
                    
                # Calculate nitrogen using the linear regression:
                # Nitrogen = 0.0328996 * SPAD + 1.29315
                nitrogen = 0.0328996 * spad + 1.29315
                
                avg_data = data.get('avg_data', {}) or {}
                
                # Classify nitrogen level
                if nitrogen < 1.80:
                    class_eq1 = 'deficient'
                elif nitrogen < 2.71:
                    class_eq1 = 'subnormal'
                elif nitrogen < 3.31:
                    class_eq1 = 'normal'
                else:
                    class_eq1 = 'high'
                    
                DeviceData.objects.create(
                    device=hist_device,
                    nitrogen=nitrogen,
                    spad=spad,
                    
                    # Store RGB
                    r=to_float(data.get('R', avg_data.get('R'))),
                    g=to_float(data.get('G', avg_data.get('G'))),
                    b=to_float(data.get('B', avg_data.get('B'))),
                    o=to_float(data.get('O', avg_data.get('O'))),
                    v=to_float(data.get('V', avg_data.get('V'))),
                    y=to_float(data.get('Y', avg_data.get('Y'))),
                    
                    class_eq1=class_eq1,
                    firebase_timestamp=firebase_timestamp
                )
                data_points_created += 1
                
    logger.info(f"Sync complete. Devices: {devices_created} created, {devices_updated} updated. Data points: {data_points_created} created.")
    return {
        'devices_created': devices_created,
        'devices_updated': devices_updated,
        'data_points_created': data_points_created
    }

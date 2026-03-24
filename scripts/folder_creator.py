# utils/folder_creator.py
"""
Auto Create Folder Structure di Google Drive
Berdasarkan workflow di Google Sheets Database_Regulasi
"""

import streamlit as st
from datetime import datetime


class FolderCreator:
    """Create folder structure automatically"""
    
    def __init__(self, drive_manager):
        self.dm = drive_manager
        self.created_folders = {}  # Cache folder yang sudah dibuat
        self.logs = []  # Log aktivitas
    
    def create_folder_structure(self):
        """
        Main function untuk create seluruh struktur folder
        
        Structure:
        ðŸ“ KATEGORI (Level 1)
          â””â”€ ðŸ“ BIDANG (Level 2)
              â””â”€ ðŸ“ UNIT (Level 3)
                  â””â”€ ðŸ“ SUBKATEGORI (Level 4)
        """
        
        try:
            # Get data from sheets
            self.log("ðŸ“‹ Membaca data dari Google Sheets...")
            
            kategoris = self._get_kategori()
            bidangs = self._get_bidang()
            units = self._get_unit()
            subkategoris = self._get_subkategori()
            
            if not kategoris:
                return False, "Tidak ada data kategori"
            
            self.log(f"âœ… Data loaded: {len(kategoris)} kategori, {len(bidangs)} bidang, {len(units)} unit, {len(subkategoris)} subkategori")
            
            # Root folder
            root_folder_id = self.dm.DRIVE_FOLDER_ID
            self.log(f"ðŸ“ Root folder: {root_folder_id}")
            
            # Create structure
            total_created = 0
            total_skipped = 0
            
            # Loop kategori (Level 1)
            for kat in kategoris:
                kat_id = kat.get('kategori_id')
                kat_name = kat.get('nama_kategori')
                
                if not kat_id or not kat_name:
                    continue
                
                # Create/Get kategori folder
                kat_folder_id = self._create_or_get_folder(
                    kat_name, 
                    root_folder_id,
                    f"KATEGORI-{kat_id}"
                )
                
                if kat_folder_id:
                    total_created += 1
                    self.log(f"  ðŸ“‚ {kat_name}")
                else:
                    total_skipped += 1
                    continue
                
                # Get bidang untuk kategori ini
                kat_bidangs = [b for b in bidangs if b.get('kategori_id') == kat_id]
                
                # Loop bidang (Level 2)
                for bid in kat_bidangs:
                    bid_id = bid.get('bidang_id')
                    bid_name = bid.get('nama_bidang')
                    has_unit = bid.get('has_unit', False)
                    
                    if not bid_id or not bid_name:
                        continue
                    
                    # Create/Get bidang folder
                    bid_folder_id = self._create_or_get_folder(
                        bid_name,
                        kat_folder_id,
                        f"BIDANG-{bid_id}"
                    )
                    
                    if bid_folder_id:
                        total_created += 1
                        self.log(f"    ðŸ“ {bid_name}")
                    else:
                        total_skipped += 1
                        continue
                    
                    # Jika bidang punya unit
                    if has_unit:
                        # Get unit untuk bidang ini
                        bid_units = [u for u in units if u.get('bidang_id') == bid_id]
                        
                        # Loop unit (Level 3)
                        for unit in bid_units:
                            unit_id = unit.get('unit_id')
                            unit_name = unit.get('nama_unit')
                            
                            if not unit_id or not unit_name:
                                continue
                            
                            # Create/Get unit folder
                            unit_folder_id = self._create_or_get_folder(
                                unit_name,
                                bid_folder_id,
                                f"UNIT-{unit_id}"
                            )
                            
                            if unit_folder_id:
                                total_created += 1
                                self.log(f"      ðŸ“„ {unit_name}")
                            else:
                                total_skipped += 1
                                continue
                            
                            # Get subkategori untuk unit ini
                            unit_subs = [s for s in subkategoris 
                                       if s.get('unit_id') == unit_id 
                                       and s.get('bidang_id') == bid_id
                                       and s.get('kategori_id') == kat_id]
                            
                            # Loop subkategori (Level 4)
                            for sub in unit_subs:
                                sub_id = sub.get('subkategori_id')
                                sub_name = sub.get('nama_subkategori')
                                
                                if not sub_id or not sub_name:
                                    continue
                                
                                # Create/Get subkategori folder
                                sub_folder_id = self._create_or_get_folder(
                                    sub_name,
                                    unit_folder_id,
                                    f"SUB-{sub_id}"
                                )
                                
                                if sub_folder_id:
                                    total_created += 1
                                    self.log(f"        ðŸ“‘ {sub_name}")
                                else:
                                    total_skipped += 1
                    
                    else:
                        # Bidang tanpa unit, langsung subkategori
                        bid_subs = [s for s in subkategoris 
                                   if s.get('bidang_id') == bid_id
                                   and s.get('kategori_id') == kat_id
                                   and (not s.get('unit_id') or str(s.get('unit_id')).lower() in ['nan', 'none', ''])]
                        
                        for sub in bid_subs:
                            sub_id = sub.get('subkategori_id')
                            sub_name = sub.get('nama_subkategori')
                            
                            if not sub_id or not sub_name:
                                continue
                            
                            sub_folder_id = self._create_or_get_folder(
                                sub_name,
                                bid_folder_id,
                                f"SUB-{sub_id}"
                            )
                            
                            if sub_folder_id:
                                total_created += 1
                                self.log(f"      ðŸ“‘ {sub_name}")
                            else:
                                total_skipped += 1
            
            # Summary
            self.log(f"\nâœ… SELESAI!")
            self.log(f"ðŸ“Š Total folder dibuat: {total_created}")
            self.log(f"â­ï¸ Total folder dilewati (sudah ada): {total_skipped}")
            
            return True, f"Berhasil! {total_created} folder dibuat, {total_skipped} sudah ada"
            
        except Exception as e:
            self.log(f"âŒ ERROR: {str(e)}")
            import traceback
            self.log(traceback.format_exc())
            return False, str(e)
    
    def _create_or_get_folder(self, folder_name, parent_id, cache_key):
        """
        Create folder jika belum ada, atau get folder_id jika sudah ada
        
        Args:
            folder_name: nama folder
            parent_id: parent folder ID
            cache_key: key untuk caching
        
        Returns:
            folder_id atau None
        """
        
        # Check cache
        if cache_key in self.created_folders:
            return self.created_folders[cache_key]
        
        try:
            # Check apakah folder sudah ada
            existing_id = self.dm.search_folder(folder_name, parent_id)
            
            if existing_id:
                # Folder sudah ada
                self.created_folders[cache_key] = existing_id
                return existing_id
            
            # Folder belum ada, buat baru
            new_folder_id = self.dm.create_folder(folder_name, parent_id)
            
            if new_folder_id:
                self.created_folders[cache_key] = new_folder_id
                return new_folder_id
            
            return None
            
        except Exception as e:
            self.log(f"  âš ï¸ Error creating '{folder_name}': {str(e)}")
            return None
    
    def _get_kategori(self):
        """Get data kategori dari sheets"""
        try:
            df = self.dm.get_master_data('kategori_id')
            if df.empty:
                return []
            
            # Filter hanya yang aktif
            df = df[df['status'].str.lower() == 'aktif']
            
            return df.to_dict('records')
        except:
            return []
    
    def _get_bidang(self):
        """Get data bidang dari sheets"""
        try:
            df = self.dm.get_master_data('bidang_id')
            if df.empty:
                return []
            
            # Filter hanya yang aktif
            df = df[df['status'].str.lower() == 'aktif']
            
            return df.to_dict('records')
        except:
            return []
    
    def _get_unit(self):
        """Get data unit dari sheets"""
        try:
            df = self.dm.get_master_data('unit_id')
            if df.empty:
                return []
            
            # Filter hanya yang aktif
            df = df[df['status'].str.lower() == 'aktif']
            
            return df.to_dict('records')
        except:
            return []
    
    def _get_subkategori(self):
        """Get data subkategori dari sheets"""
        try:
            df = self.dm.get_master_data('subkategori_id')
            if df.empty:
                return []
            
            # Filter hanya yang aktif
            df = df[df['status'].str.lower() == 'aktif']
            
            return df.to_dict('records')
        except:
            return []
    
    def log(self, message):
        """Add log message"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        log_msg = f"[{timestamp}] {message}"
        self.logs.append(log_msg)
        print(log_msg)
    
    def get_logs(self):
        """Get all logs"""
        return "\n".join(self.logs)
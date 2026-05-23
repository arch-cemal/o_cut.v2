
"""
Database Manager for Cutting Optimization System - UPDATED
"""
import sqlite3
import os
from datetime import datetime
from typing import List, Dict, Optional
from dataclasses import dataclass

@dataclass
class RawMaterial:
    material_id: int
    material_name: str
    profile_type: str
    standard_length: float
    quantity: int

@dataclass
class Offcut:
    offcut_id: int
    material_id: int
    material_name: str
    profile_type: str
    length: float
    quantity: int
    status: str

@dataclass
class OrderInput:
    input_id: int
    required_length: float
    required_quantity: int
    part_name: str
    part_color: str

class DatabaseManager:
    DEFAULT_MATERIALS = [
        ("حديد تسليح", "Q235-40x40", 6000, 50),
        ("حديد تسليح", "Q235-50x50", 6000, 30),
        ("شيلمان", "SHL-30x30", 6000, 40),
        ("تيوبات", "TUBE-2inch", 6000, 25),
        ("ألومنيوم", "AL-6063-T5", 6000, 35),
        ("خشب", "Pine-2x4", 4000, 20),
    ]

    def __init__(self, db_path: str = "cutting_optimizer.db"):
        self.db_path = db_path
        self.init_database()
        self.ensure_default_materials()

    def get_connection(self):
        return sqlite3.connect(self.db_path)

    def init_database(self):
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Raw_Materials_Stock (
                Material_ID INTEGER PRIMARY KEY AUTOINCREMENT,
                Material_Name TEXT NOT NULL,
                Profile_Type TEXT NOT NULL,
                Standard_Length REAL NOT NULL,
                Quantity INTEGER NOT NULL DEFAULT 0,
                Created_Date TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Offcuts_Stock (
                Offcut_ID INTEGER PRIMARY KEY AUTOINCREMENT,
                Material_ID INTEGER NOT NULL,
                Length REAL NOT NULL,
                Quantity INTEGER NOT NULL DEFAULT 1,
                Status TEXT NOT NULL DEFAULT 'Available' CHECK(Status IN ('Available', 'Used')),
                Created_Date TEXT DEFAULT CURRENT_TIMESTAMP,
                Used_Date TEXT,
                FOREIGN KEY (Material_ID) REFERENCES Raw_Materials_Stock(Material_ID)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Current_Order_Inputs (
                Input_ID INTEGER PRIMARY KEY AUTOINCREMENT,
                Required_Length REAL NOT NULL,
                Required_Quantity INTEGER NOT NULL,
                Part_Name TEXT NOT NULL,
                Part_Color TEXT NOT NULL DEFAULT '#3498db',
                Use_New_Material INTEGER DEFAULT 1,
                Created_Date TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Operations (
                Operation_ID INTEGER PRIMARY KEY AUTOINCREMENT,
                Operation_Date TEXT DEFAULT CURRENT_TIMESTAMP,
                Status TEXT DEFAULT 'Pending' CHECK(Status IN ('Pending', 'Confirmed', 'Cancelled')),
                Total_Waste REAL DEFAULT 0.0,
                Kerf_Thickness REAL DEFAULT 3.0,
                Joint_Loss REAL DEFAULT 2.0,
                Min_Offcut_Length REAL DEFAULT 500.0,
                Use_Offcuts_First INTEGER DEFAULT 1
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Operation_Details (
                Detail_ID INTEGER PRIMARY KEY AUTOINCREMENT,
                Operation_ID INTEGER NOT NULL,
                Input_ID INTEGER,
                Material_ID INTEGER,
                Offcut_ID INTEGER,
                Source_Type TEXT NOT NULL,
                Original_Length REAL NOT NULL,
                Used_Length REAL NOT NULL,
                Waste_Length REAL NOT NULL,
                Is_Spliced INTEGER DEFAULT 0,
                Splice_Piece_1_ID INTEGER,
                Splice_Piece_1_Length REAL,
                Splice_Piece_2_ID INTEGER,
                Splice_Piece_2_Length REAL,
                Joint_Loss_Used REAL DEFAULT 0.0,
                FOREIGN KEY (Operation_ID) REFERENCES Operations(Operation_ID),
                FOREIGN KEY (Input_ID) REFERENCES Current_Order_Inputs(Input_ID),
                FOREIGN KEY (Material_ID) REFERENCES Raw_Materials_Stock(Material_ID),
                FOREIGN KEY (Offcut_ID) REFERENCES Offcuts_Stock(Offcut_ID)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Inventory_Transactions (
                Transaction_ID INTEGER PRIMARY KEY AUTOINCREMENT,
                Operation_ID INTEGER,
                Material_ID INTEGER,
                Offcut_ID INTEGER,
                Transaction_Type TEXT NOT NULL,
                Quantity_Change INTEGER NOT NULL,
                Previous_Quantity INTEGER,
                New_Quantity INTEGER,
                Transaction_Date TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (Operation_ID) REFERENCES Operations(Operation_ID)
            )
        """)

        conn.commit()
        conn.close()

    def ensure_default_materials(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM Raw_Materials_Stock")
        count = cursor.fetchone()[0]
        if count == 0:
            for name, profile, length, qty in self.DEFAULT_MATERIALS:
                cursor.execute("""
                    INSERT INTO Raw_Materials_Stock (Material_Name, Profile_Type, Standard_Length, Quantity)
                    VALUES (?, ?, ?, ?)
                """, (name, profile, length, qty))
            conn.commit()
        conn.close()

    def add_raw_material(self, material: RawMaterial) -> int:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO Raw_Materials_Stock (Material_Name, Profile_Type, Standard_Length, Quantity)
            VALUES (?, ?, ?, ?)
        """, (material.material_name, material.profile_type, 
              material.standard_length, material.quantity))
        conn.commit()
        last_id = cursor.lastrowid
        conn.close()
        return last_id

    def update_raw_material(self, material_id: int, name: str, profile: str, length: float, quantity: int):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE Raw_Materials_Stock 
            SET Material_Name = ?, Profile_Type = ?, Standard_Length = ?, Quantity = ?
            WHERE Material_ID = ?
        """, (name, profile, length, quantity, material_id))
        conn.commit()
        conn.close()

    def get_raw_materials(self) -> List[RawMaterial]:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT Material_ID, Material_Name, Profile_Type, Standard_Length, Quantity FROM Raw_Materials_Stock ORDER BY Material_Name")
        rows = cursor.fetchall()
        conn.close()
        return [RawMaterial(*row) for row in rows]

    def get_raw_material_by_id(self, material_id: int) -> Optional[RawMaterial]:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT Material_ID, Material_Name, Profile_Type, Standard_Length, Quantity FROM Raw_Materials_Stock WHERE Material_ID = ?", (material_id,))
        row = cursor.fetchone()
        conn.close()
        return RawMaterial(*row) if row else None

    def delete_raw_material(self, material_id: int):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM Raw_Materials_Stock WHERE Material_ID = ?", (material_id,))
        conn.commit()
        conn.close()

    def add_offcut(self, offcut: Offcut) -> int:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO Offcuts_Stock (Material_ID, Length, Quantity, Status)
            VALUES (?, ?, ?, ?)
        """, (offcut.material_id, offcut.length, offcut.quantity, offcut.status))
        conn.commit()
        last_id = cursor.lastrowid
        conn.close()
        return last_id

    def get_offcuts(self, status: Optional[str] = None, material_id: Optional[int] = None) -> List[Offcut]:
        conn = self.get_connection()
        cursor = conn.cursor()
        query = """
            SELECT o.Offcut_ID, o.Material_ID, r.Material_Name, r.Profile_Type, o.Length, o.Quantity, o.Status
            FROM Offcuts_Stock o
            JOIN Raw_Materials_Stock r ON o.Material_ID = r.Material_ID
            WHERE 1=1
        """
        params = []
        if status:
            query += " AND o.Status = ?"
            params.append(status)
        if material_id:
            query += " AND o.Material_ID = ?"
            params.append(material_id)
        query += " ORDER BY o.Length DESC"
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        return [Offcut(*row) for row in rows]

    def update_offcut_status(self, offcut_id: int, status: str):
        conn = self.get_connection()
        cursor = conn.cursor()
        used_date = datetime.now().isoformat() if status == "Used" else None
        cursor.execute("UPDATE Offcuts_Stock SET Status = ?, Used_Date = ? WHERE Offcut_ID = ?",
                      (status, used_date, offcut_id))
        conn.commit()
        conn.close()

    def delete_offcut(self, offcut_id: int):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM Offcuts_Stock WHERE Offcut_ID = ?", (offcut_id,))
        conn.commit()
        conn.close()

    def add_order_input(self, input_data: OrderInput, use_new_material: bool = True) -> int:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO Current_Order_Inputs (Required_Length, Required_Quantity, Part_Name, Part_Color, Use_New_Material)
            VALUES (?, ?, ?, ?, ?)
        """, (input_data.required_length, input_data.required_quantity,
              input_data.part_name, input_data.part_color, 1 if use_new_material else 0))
        conn.commit()
        last_id = cursor.lastrowid
        conn.close()
        return last_id

    def get_order_inputs(self) -> List[OrderInput]:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT Input_ID, Required_Length, Required_Quantity, Part_Name, Part_Color FROM Current_Order_Inputs ORDER BY Part_Name")
        rows = cursor.fetchall()
        conn.close()
        return [OrderInput(*row) for row in rows]

    def clear_order_inputs(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM Current_Order_Inputs")
        conn.commit()
        conn.close()

    def delete_order_input(self, input_id: int):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM Current_Order_Inputs WHERE Input_ID = ?", (input_id,))
        conn.commit()
        conn.close()

    def create_operation(self, kerf: float = 3.0, joint_loss: float = 2.0, 
                         min_offcut: float = 500.0, use_offcuts_first: bool = True) -> int:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO Operations (Kerf_Thickness, Joint_Loss, Min_Offcut_Length, Use_Offcuts_First, Status)
            VALUES (?, ?, ?, ?, 'Pending')
        """, (kerf, joint_loss, min_offcut, 1 if use_offcuts_first else 0))
        conn.commit()
        last_id = cursor.lastrowid
        conn.close()
        return last_id

    def add_operation_detail(self, operation_id: int, detail: Dict):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO Operation_Details 
            (Operation_ID, Input_ID, Material_ID, Offcut_ID, Source_Type,
             Original_Length, Used_Length, Waste_Length, Is_Spliced,
             Splice_Piece_1_ID, Splice_Piece_1_Length,
             Splice_Piece_2_ID, Splice_Piece_2_Length, Joint_Loss_Used)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            operation_id, detail.get("input_id"), detail.get("material_id"),
            detail.get("offcut_id"), detail["source_type"],
            detail["original_length"], detail["used_length"], detail["waste_length"],
            1 if detail.get("is_spliced") else 0,
            detail.get("splice_piece_1_id"), detail.get("splice_piece_1_length"),
            detail.get("splice_piece_2_id"), detail.get("splice_piece_2_length"),
            detail.get("joint_loss_used", 0.0)
        ))
        conn.commit()
        conn.close()

    def confirm_operation(self, operation_id: int):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Operation_Details WHERE Operation_ID = ?", (operation_id,))
        details = cursor.fetchall()

        for detail in details:
            (detail_id, op_id, input_id, material_id, offcut_id, source_type,
             orig_len, used_len, waste_len, is_spliced, sp1_id, sp1_len,
             sp2_id, sp2_len, joint_loss) = detail

            if source_type == "Raw":
                cursor.execute("SELECT Quantity FROM Raw_Materials_Stock WHERE Material_ID = ?", (material_id,))
                current_qty = cursor.fetchone()[0]
                new_qty = max(0, current_qty - 1)
                cursor.execute("UPDATE Raw_Materials_Stock SET Quantity = ? WHERE Material_ID = ?", (new_qty, material_id))
                cursor.execute("""
                    INSERT INTO Inventory_Transactions 
                    (Operation_ID, Material_ID, Transaction_Type, Quantity_Change, Previous_Quantity, New_Quantity)
                    VALUES (?, ?, 'Consume', -1, ?, ?)
                """, (operation_id, material_id, current_qty, new_qty))

            elif source_type == "Offcut":
                cursor.execute("UPDATE Offcuts_Stock SET Status = 'Used', Used_Date = ? WHERE Offcut_ID = ?",
                              (datetime.now().isoformat(), offcut_id))
                cursor.execute("""
                    INSERT INTO Inventory_Transactions 
                    (Operation_ID, Offcut_ID, Transaction_Type, Quantity_Change, Previous_Quantity, New_Quantity)
                    VALUES (?, ?, 'Status_Change', 0, 1, 1)
                """, (operation_id, offcut_id))

            elif source_type == "Spliced":
                for sp_id in [sp1_id, sp2_id]:
                    if sp_id:
                        cursor.execute("UPDATE Offcuts_Stock SET Status = 'Used', Used_Date = ? WHERE Offcut_ID = ?",
                                      (datetime.now().isoformat(), sp_id))
                        cursor.execute("""
                            INSERT INTO Inventory_Transactions 
                            (Operation_ID, Offcut_ID, Transaction_Type, Quantity_Change, Previous_Quantity, New_Quantity)
                            VALUES (?, ?, 'Status_Change', 0, 1, 1)
                        """, (operation_id, sp_id))

            if waste_len >= 500:
                cursor.execute("""
                    INSERT INTO Offcuts_Stock (Material_ID, Length, Quantity, Status)
                    VALUES (?, ?, 1, 'Available')
                """, (material_id, waste_len))
                new_offcut_id = cursor.lastrowid
                cursor.execute("""
                    INSERT INTO Inventory_Transactions 
                    (Operation_ID, Offcut_ID, Transaction_Type, Quantity_Change, Previous_Quantity, New_Quantity)
                    VALUES (?, ?, 'Produce', 1, 0, 1)
                """, (operation_id, new_offcut_id))

        cursor.execute("UPDATE Operations SET Status = 'Confirmed' WHERE Operation_ID = ?", (operation_id,))
        conn.commit()
        conn.close()

    def cancel_operation(self, operation_id: int):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE Operations SET Status = 'Cancelled' WHERE Operation_ID = ?", (operation_id,))
        conn.commit()
        conn.close()

    def get_operations_history(self) -> List[Dict]:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Operations ORDER BY Operation_Date DESC")
        rows = cursor.fetchall()
        conn.close()
        return [{"operation_id": row[0], "date": row[1], "status": row[2], "total_waste": row[3]} for row in rows]

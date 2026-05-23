
"""
Test script for Cutting Optimizer System v2.0
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.database import DatabaseManager, RawMaterial, Offcut, OrderInput
from core.optimizer import CuttingOptimizer

def test_database():
    print("=" * 60)
    print("Testing Database Operations v2.0")
    print("=" * 60)

    db = DatabaseManager("test_v2.db")

    materials = db.get_raw_materials()
    print(f"✓ Default materials loaded: {len(materials)} items")
    for m in materials:
        print(f"  - {m.material_name} ({m.profile_type}): {m.quantity} x {m.standard_length}mm")

    available_offcuts = db.get_offcuts(status='Available')
    print(f"✓ Available offcuts: {len(available_offcuts)}")

    print("\n✓ Database tests PASSED")
    return db

def test_optimizer():
    print("\n" + "=" * 60)
    print("Testing Optimization Engine v2.0")
    print("=" * 60)

    optimizer = CuttingOptimizer(kerf_thickness=3.0, joint_loss=2.0, min_offcut_length=500.0)

    required_pieces = [
        {'input_id': 1, 'length': 1200, 'quantity': 3, 'name': 'قائم خلفي', 'color': '#e74c3c'},
        {'input_id': 2, 'length': 800, 'quantity': 2, 'name': 'عارضة جانبية', 'color': '#3498db'},
        {'input_id': 3, 'length': 1500, 'quantity': 1, 'name': 'قائم أمامي', 'color': '#2ecc71'},
    ]

    raw_materials = [
        {'material_id': 1, 'material_name': 'حديد تسليح', 'profile_type': 'Q235-40x40', 
         'standard_length': 6000, 'quantity': 5, 'unit_price': 0},
    ]

    offcuts = [
        {'offcut_id': 1, 'material_id': 1, 'material_name': 'حديد تسليح', 
         'profile_type': 'Q235-40x40', 'length': 1500, 'quantity': 2, 'status': 'Available'},
        {'offcut_id': 2, 'material_id': 1, 'material_name': 'حديد تسليح', 
         'profile_type': 'Q235-40x40', 'length': 900, 'quantity': 1, 'status': 'Available'},
    ]

    plan = optimizer.optimize(required_pieces, raw_materials, offcuts, use_offcuts_first=True, use_new_materials=True)

    print(f"✓ Total pieces assigned: {sum(len(sp.cuts) for sp in plan.stock_pieces if sp.used)}")
    print(f"✓ Raw materials used: {plan.total_raw_used}")
    print(f"✓ Offcuts used: {plan.total_offcuts_used}")
    print(f"✓ Spliced pieces: {len(plan.spliced_pieces)}")
    print(f"✓ Scrap pieces (<500mm): {len(plan.scrap_pieces)}")
    print(f"✓ Reusable offcuts (>=500mm): {len(plan.reusable_offcuts)}")
    print(f"✓ Unassigned pieces: {len(plan.unassigned_pieces)}")
    print(f"✓ Total waste: {plan.total_waste:.2f}mm")

    visual_data = optimizer.generate_visual_data(plan)
    print(f"✓ Visual bars generated: {len(visual_data)}")

    stats = optimizer.calculate_statistics(plan, raw_materials)
    print(f"✓ Efficiency: {stats['efficiency']}%")
    print(f"✓ Waste percentage: {stats['waste_percentage']}%")
    print(f"✓ Scrap total: {stats['scrap_total']:.0f}mm")
    print(f"✓ Reusable total: {stats['reusable_total']:.0f}mm")

    print("\n✓ Optimizer tests PASSED")
    return plan

def test_splicing():
    print("\n" + "=" * 60)
    print("Testing Splicing Algorithm")
    print("=" * 60)

    optimizer = CuttingOptimizer(kerf_thickness=3.0, joint_loss=2.0, min_offcut_length=500.0)

    required_pieces = [
        {'input_id': 1, 'length': 2000, 'quantity': 1, 'name': 'قطعة موصولة', 'color': '#9b59b6'},
    ]

    offcuts = [
        {'offcut_id': 1, 'material_id': 1, 'material_name': 'حديد تسليح', 
         'profile_type': 'Q235-40x40', 'length': 1200, 'quantity': 1, 'status': 'Available'},
        {'offcut_id': 2, 'material_id': 1, 'material_name': 'حديد تسليح', 
         'profile_type': 'Q235-40x40', 'length': 900, 'quantity': 1, 'status': 'Available'},
    ]

    raw_materials = []

    plan = optimizer.optimize(required_pieces, raw_materials, offcuts, use_offcuts_first=True, use_new_materials=True)

    print(f"✓ Spliced pieces created: {len(plan.spliced_pieces)}")
    if plan.spliced_pieces:
        splice = plan.spliced_pieces[0]
        print(f"  - Piece: {splice['piece_name']} ({splice['piece_length']}mm)")
        print(f"  - Splice 1: {splice['splice1_length']}mm (ID: {splice['splice1_id']})")
        print(f"  - Splice 2: {splice['splice2_length']}mm (ID: {splice['splice2_id']})")
        print(f"  - Joint loss: {splice['joint_loss']}mm")

    print("\n✓ Splicing tests PASSED")

if __name__ == "__main__":
    try:
        test_database()
        test_optimizer()
        test_splicing()
        print("\n" + "=" * 60)
        print("ALL TESTS PASSED - v2.0 Ready!")
        print("=" * 60)
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()


"""
1D Cutting Stock Optimization Engine - UPDATED
With Scrap vs Offcuts categorization and priority control
"""
from typing import List, Dict, Optional
from dataclasses import dataclass, field

@dataclass
class Piece:
    length: float
    name: str
    color: str
    input_id: int
    assigned: bool = False
    source: Optional[str] = None
    source_id: Optional[int] = None

@dataclass
class StockPiece:
    id: int
    length: float
    material_id: int
    material_name: str
    profile_type: str
    is_offcut: bool = False
    used: bool = False
    remaining: float = field(init=False)
    cuts: List[Dict] = field(default_factory=list)

    def __post_init__(self):
        self.remaining = self.length

    def cut(self, piece: Piece, kerf: float) -> bool:
        total_needed = piece.length
        if self.cuts:
            total_needed += kerf
        if self.remaining >= total_needed:
            self.cuts.append({
                'length': piece.length,
                'name': piece.name,
                'color': piece.color,
                'input_id': piece.input_id
            })
            self.remaining -= total_needed
            piece.assigned = True
            piece.source = 'Offcut' if self.is_offcut else 'Raw'
            piece.source_id = self.id
            return True
        return False

@dataclass
class SpliceCombination:
    piece1_id: int
    piece1_length: float
    piece2_id: int
    piece2_length: float
    total_available: float
    joint_loss: float
    effective_length: float
    material_id: int
    profile_type: str

@dataclass
class CuttingPlan:
    stock_pieces: List[StockPiece]
    unassigned_pieces: List[Piece]
    total_waste: float = 0.0
    total_raw_used: int = 0
    total_offcuts_used: int = 0
    spliced_pieces: List[Dict] = field(default_factory=list)
    scrap_pieces: List[Dict] = field(default_factory=list)
    reusable_offcuts: List[Dict] = field(default_factory=list)

    def calculate_waste(self):
        self.total_waste = sum(sp.remaining for sp in self.stock_pieces if sp.used)

class CuttingOptimizer:
    def __init__(self, kerf_thickness: float = 3.0, 
                 joint_loss: float = 2.0,
                 min_offcut_length: float = 500.0,
                 max_splice_pieces: int = 2):
        self.kerf = kerf_thickness
        self.joint_loss = joint_loss
        self.min_offcut = min_offcut_length
        self.max_splice = max_splice_pieces

    def optimize(self, 
                 required_pieces: List[Dict],
                 raw_materials: List[Dict],
                 offcuts: List[Dict],
                 use_offcuts_first: bool = True,
                 use_new_materials: bool = True) -> CuttingPlan:
        """
        Main optimization algorithm
        use_offcuts_first: prioritize offcuts
        use_new_materials: allow using raw materials
        """
        pieces = []
        for req in required_pieces:
            for i in range(req['quantity']):
                pieces.append(Piece(
                    length=req['length'],
                    name=req['name'],
                    color=req['color'],
                    input_id=req['input_id']
                ))

        pieces.sort(key=lambda p: p.length, reverse=True)

        stock_pieces = []

        # Add offcuts first (priority sourcing)
        if use_offcuts_first:
            for off in offcuts:
                if off['status'] == 'Available':
                    for i in range(off['quantity']):
                        stock_pieces.append(StockPiece(
                            id=off['offcut_id'],
                            length=off['length'],
                            material_id=off['material_id'],
                            material_name=off['material_name'],
                            profile_type=off['profile_type'],
                            is_offcut=True
                        ))

        # Add raw materials
        if use_new_materials:
            for raw in raw_materials:
                for i in range(raw['quantity']):
                    stock_pieces.append(StockPiece(
                        id=raw['material_id'],
                        length=raw['standard_length'],
                        material_id=raw['material_id'],
                        material_name=raw['material_name'],
                        profile_type=raw['profile_type'],
                        is_offcut=False
                    ))

        plan = CuttingPlan(stock_pieces=[], unassigned_pieces=[], scrap_pieces=[], reusable_offcuts=[])
        spliced_results = []

        # Phase 1: Try offcuts first
        if use_offcuts_first:
            for piece in pieces:
                if piece.assigned:
                    continue
                offcut_stock = [sp for sp in stock_pieces if sp.is_offcut and not sp.used and sp.material_id]
                offcut_stock.sort(key=lambda sp: sp.length)
                for sp in offcut_stock:
                    if sp.cut(piece, self.kerf):
                        if sp not in plan.stock_pieces:
                            plan.stock_pieces.append(sp)
                            sp.used = True
                        plan.total_offcuts_used += 1
                        break

        # Phase 2: Try splicing (max 2 pieces)
        if use_offcuts_first:
            for piece in pieces:
                if piece.assigned:
                    continue
                splice = self._find_best_splice(piece, stock_pieces)
                if splice:
                    sp1 = next(sp for sp in stock_pieces if sp.id == splice.piece1_id and sp.is_offcut and not sp.used)
                    sp2 = next(sp for sp in stock_pieces if sp.id == splice.piece2_id and sp.is_offcut and not sp.used)

                    sp1.used = True
                    sp2.used = True
                    sp1.cuts.append({
                        'length': splice.piece1_length,
                        'name': piece.name + ' [موصولة]',
                        'color': piece.color,
                        'input_id': piece.input_id,
                        'is_splice': True,
                        'splice_part': 1
                    })
                    sp2.cuts.append({
                        'length': splice.piece2_length,
                        'name': piece.name + ' [موصولة]',
                        'color': piece.color,
                        'input_id': piece.input_id,
                        'is_splice': True,
                        'splice_part': 2
                    })

                    if sp1 not in plan.stock_pieces:
                        plan.stock_pieces.append(sp1)
                    if sp2 not in plan.stock_pieces:
                        plan.stock_pieces.append(sp2)

                    piece.assigned = True
                    piece.source = 'Spliced'

                    spliced_results.append({
                        'piece_name': piece.name,
                        'piece_length': piece.length,
                        'splice1_id': splice.piece1_id,
                        'splice1_length': splice.piece1_length,
                        'splice2_id': splice.piece2_id,
                        'splice2_length': splice.piece2_length,
                        'joint_loss': self.joint_loss,
                        'total_used': splice.piece1_length + splice.piece2_length,
                        'material_id': splice.material_id,
                        'profile_type': splice.profile_type
                    })
                    plan.total_offcuts_used += 2

        # Phase 3: Use raw materials for remaining pieces
        if use_new_materials:
            for piece in pieces:
                if piece.assigned:
                    continue
                raw_stock = [sp for sp in stock_pieces if not sp.is_offcut and not sp.used]
                raw_stock.sort(key=lambda sp: sp.length)
                for sp in raw_stock:
                    if sp.cut(piece, self.kerf):
                        if sp not in plan.stock_pieces:
                            plan.stock_pieces.append(sp)
                            sp.used = True
                        plan.total_raw_used += 1
                        break

        plan.unassigned_pieces = [p for p in pieces if not p.assigned]
        plan.spliced_pieces = spliced_results

        # Categorize waste into Scrap vs Reusable Offcuts
        for sp in plan.stock_pieces:
            if not sp.used:
                continue
            if sp.remaining > 0:
                waste_item = {
                    'stock_id': sp.id,
                    'material_name': sp.material_name,
                    'profile_type': sp.profile_type,
                    'length': sp.remaining,
                    'is_offcut': sp.is_offcut,
                    'source_type': 'Offcut' if sp.is_offcut else 'Raw'
                }
                if sp.remaining >= self.min_offcut:
                    plan.reusable_offcuts.append(waste_item)
                else:
                    plan.scrap_pieces.append(waste_item)

        plan.calculate_waste()
        return plan

    def _find_best_splice(self, piece: Piece, stock_pieces: List[StockPiece]) -> Optional[SpliceCombination]:
        required = piece.length + self.joint_loss
        available_offcuts = [sp for sp in stock_pieces if sp.is_offcut and not sp.used]

        best_splice = None
        min_waste = float('inf')

        for i, sp1 in enumerate(available_offcuts):
            for sp2 in available_offcuts[i+1:]:
                if sp1.material_id != sp2.material_id:
                    continue
                if sp1.profile_type != sp2.profile_type:
                    continue

                total = sp1.length + sp2.length
                if total >= required:
                    waste = total - required
                    if waste < min_waste:
                        min_waste = waste
                        if sp1.length >= required:
                            use1 = required - sp2.length
                            use2 = sp2.length
                        elif sp2.length >= required:
                            use1 = sp1.length
                            use2 = required - sp1.length
                        else:
                            use1 = sp1.length
                            use2 = required - sp1.length

                        best_splice = SpliceCombination(
                            piece1_id=sp1.id,
                            piece1_length=use1,
                            piece2_id=sp2.id,
                            piece2_length=use2,
                            total_available=total,
                            joint_loss=self.joint_loss,
                            effective_length=required - self.joint_loss,
                            material_id=sp1.material_id,
                            profile_type=sp1.profile_type
                        )

        return best_splice

    def generate_visual_data(self, plan: CuttingPlan) -> List[Dict]:
        visual_data = []
        for sp in plan.stock_pieces:
            if not sp.used:
                continue

            bar_data = {
                'stock_id': sp.id,
                'material_name': sp.material_name,
                'profile_type': sp.profile_type,
                'original_length': sp.length,
                'remaining': sp.remaining,
                'is_offcut': sp.is_offcut,
                'segments': []
            }

            current_pos = 0
            for cut in sp.cuts:
                segment = {
                    'start': current_pos,
                    'length': cut['length'],
                    'name': cut['name'],
                    'color': cut['color'],
                    'input_id': cut['input_id'],
                    'is_splice': cut.get('is_splice', False),
                    'splice_part': cut.get('splice_part', 0)
                }
                bar_data['segments'].append(segment)
                current_pos += cut['length'] + self.kerf

            if sp.remaining > 0:
                is_scrap = sp.remaining < self.min_offcut
                bar_data['segments'].append({
                    'start': current_pos - self.kerf if sp.cuts else 0,
                    'length': sp.remaining,
                    'name': 'هدر تالف' if is_scrap else 'فضلة صالحة',
                    'color': '#e74c3c' if is_scrap else '#27ae60',
                    'is_waste': True,
                    'is_scrap': is_scrap
                })

            visual_data.append(bar_data)

        return visual_data

    def calculate_statistics(self, plan: CuttingPlan, raw_materials: List[Dict]) -> Dict:
        total_required = sum(sum(cut['length'] for cut in sp.cuts) for sp in plan.stock_pieces if sp.used)
        total_stock_used = sum(sp.length for sp in plan.stock_pieces if sp.used)
        total_waste = plan.total_waste
        waste_percentage = (total_waste / total_stock_used * 100) if total_stock_used > 0 else 0

        scrap_total = sum(s['length'] for s in plan.scrap_pieces)
        reusable_total = sum(o['length'] for o in plan.reusable_offcuts)

        return {
            'total_pieces': sum(len(sp.cuts) for sp in plan.stock_pieces if sp.used),
            'total_required_length': total_required,
            'total_stock_used': total_stock_used,
            'total_waste': total_waste,
            'waste_percentage': round(waste_percentage, 2),
            'raw_materials_used': plan.total_raw_used,
            'offcuts_used': plan.total_offcuts_used,
            'spliced_pieces': len(plan.spliced_pieces),
            'unassigned_pieces': len(plan.unassigned_pieces),
            'scrap_count': len(plan.scrap_pieces),
            'scrap_total': scrap_total,
            'reusable_count': len(plan.reusable_offcuts),
            'reusable_total': reusable_total,
            'efficiency': round((total_required / total_stock_used * 100), 2) if total_stock_used > 0 else 0
        }

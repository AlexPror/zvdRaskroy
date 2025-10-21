#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Конфигурация расчета отверстий труб в зависимости от B4
"""

def calculate_otv_trub(B4: float) -> dict:
    """
    Расчет количества отверстий и шага
    
    Args:
        B4: Параметр B4 (мм)
    
    Returns:
        dict: {'chisloOtvTrub': int, 'shagOtv': float}
    """
    
    # Правило 1: B4 от 160 до <180
    if 160 <= B4 < 180:
        return {
            'chisloOtvTrub': 2,
            'shagOtv': 40.5
        }
    
    # Правило 2: B4 от 180 до <250 (3 отверстия)
    if 180 <= B4 < 250:
        # Шаг: 26.5 + (B4-180)/10 * 2
        shag = 26.5 + ((B4 - 180) / 10) * 2
        return {
            'chisloOtvTrub': 3,
            'shagOtv': round(shag, 1)
        }
    
    # Правило 3: B4 от 250 до <310 (4 отверстия)
    if 250 <= B4 < 310:
        # Исключение для B4=270
        if B4 == 270:
            shag = 31.5
        else:
            # Шаг: 28.5 + (B4-250)/10 * 2
            shag = 28.5 + ((B4 - 250) / 10) * 2
        return {
            'chisloOtvTrub': 4,
            'shagOtv': round(shag, 1)
        }
    
    # Правило 4: B4 от 310+ (5 отверстий)
    if B4 >= 310:
        # Шаг: 28.5 + (B4-310)/10 * 1
        shag = 28.5 + ((B4 - 310) / 10) * 1
        return {
            'chisloOtvTrub': 5,
            'shagOtv': round(shag, 1)
        }
    
    # По умолчанию (для B4 < 160)
    return {
        'chisloOtvTrub': 2,
        'shagOtv': 40.5
    }


# Таблица значений для проверки
VERIFICATION_TABLE = [
    (160, 2, 40.5),
    (170, 2, 40.5),
    (180, 3, 26.5),
    (190, 3, 28.5),
    (200, 3, 30.5),
    (210, 3, 32.5),
    (220, 3, 34.5),
    (230, 3, 36.5),
    (240, 3, 38.5),
    (250, 4, 28.5),
    (260, 4, 30.5),
    (270, 4, 31.5),  # Исключение!
    (280, 4, 32.5),
    (290, 4, 34.5),
    (300, 4, 36.5),
    (310, 5, 28.5),
    (320, 5, 30.5),
    (330, 5, 31.5),
    (340, 5, 32.5),
    (350, 5, 33.5),
    (360, 5, 34.5),
    (370, 5, 35.5),
    (380, 5, 36.5),
    (390, 5, 37.5),
    (400, 5, 38.5),
    (410, 5, 39.5),
    (420, 5, 40.5),
]


def verify_calculation():
    """Проверка правильности расчетов"""
    import sys
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    
    print("="*70)
    print("ПРОВЕРКА РАСЧЕТА ОТВЕРСТИЙ")
    print("="*70)
    print(f"{'B4':>5} | {'Число':>5} | {'Шаг':>6} | {'Ожидается':>20} | {'Статус':>8}")
    print("-"*70)
    
    errors = []
    
    for b4, expected_chislo, expected_shag in VERIFICATION_TABLE:
        result = calculate_otv_trub(b4)
        chislo = result['chisloOtvTrub']
        shag = result['shagOtv']
        
        status = "OK" if (chislo == expected_chislo and abs(shag - expected_shag) < 0.1) else "ERR"
        expected_str = f"{expected_chislo} отв, {expected_shag}мм"
        
        print(f"{b4:5d} | {chislo:5d} | {shag:6.1f} | {expected_str:>20} | {status:>8}")
        
        if status == "ERR":
            errors.append((b4, expected_chislo, expected_shag, chislo, shag))
    
    print("="*70)
    
    if errors:
        print(f"\n❌ ОШИБОК: {len(errors)}")
        for b4, exp_c, exp_s, got_c, got_s in errors:
            print(f"  B4={b4}: ожидалось {exp_c} отв, {exp_s}мм; получено {got_c} отв, {got_s}мм")
    else:
        print("\n✅ ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ!")
    
    return len(errors) == 0


if __name__ == "__main__":
    # Проверка
    verify_calculation()
    
    # Примеры использования
    print("\n" + "="*70)
    print("ПРИМЕРЫ РАСЧЕТА:")
    print("="*70)
    
    test_values = [165, 185, 195, 255, 270, 315, 405]
    
    for b4 in test_values:
        result = calculate_otv_trub(b4)
        print(f"B4 = {b4:3d} → {result['chisloOtvTrub']} отверстий, шаг {result['shagOtv']:.1f} мм")


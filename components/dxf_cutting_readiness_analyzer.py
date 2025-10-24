#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Анализатор готовности DXF файлов к лазерной резке
Проверяет файлы на наличие проблемных элементов:
- Текстовые примитивы (TEXT, MTEXT)
- Толстые линии (thickness > 0)
- Непреобразованные полилинии
- Неподходящие для резки элементы
"""

import os
import ezdxf
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class CuttingReadinessIssue:
    """Проблема готовности к резке"""
    type: str  # 'text', 'thick_line', 'unconverted_polyline', 'unsuitable_entity'
    entity_type: str  # Тип DXF сущности
    description: str  # Описание проблемы
    recommendation: str  # Рекомендация по исправлению
    severity: str  # 'warning', 'error', 'info'


@dataclass
class CuttingReadinessReport:
    """Отчет о готовности к резке"""
    filepath: str
    filename: str
    is_ready: bool  # Готов ли файл к резке
    issues: List[CuttingReadinessIssue]
    total_entities: int
    problematic_entities: int
    readiness_score: float  # 0-100% готовности


class DXFCuttingReadinessAnalyzer:
    """Анализатор готовности DXF файлов к лазерной резке"""
    
    def __init__(self):
        # Максимальная толщина линии для резки (мм)
        self.MAX_CUTTING_THICKNESS = 0.1  # 0.1мм - стандарт для лазерной резки
        
        # Проблемные типы сущностей
        self.PROBLEMATIC_ENTITY_TYPES = {
            'TEXT': 'Текстовые примитивы не вырезаются лазером',
            'MTEXT': 'Многострочный текст не вырезается лазером',
            'DIMENSION': 'Размеры не вырезаются лазером',
            'LEADER': 'Выноски не вырезаются лазером',
            'HATCH': 'Штриховка может быть проблематичной',
            'SOLID': 'Заливки не вырезаются лазером'
        }
        
        # Критичные проблемы (более серьезные)
        self.CRITICAL_ISSUES = {
            'unclosed_contour': 'Незамкнутые контуры - КРИТИЧНО для резки!',
            'thick_line': 'Толстые линии - не подходят для резки',
            'text': 'Текстовые элементы - не будут вырезаны'
        }
    
    def analyze_file(self, filepath: str) -> CuttingReadinessReport:
        """
        Анализ DXF файла на готовность к лазерной резке
        
        Args:
            filepath: Путь к DXF файлу
            
        Returns:
            Отчет о готовности к резке
        """
        issues = []
        total_entities = 0
        problematic_entities = 0
        
        try:
            # Загружаем DXF файл
            doc = ezdxf.readfile(filepath)
            msp = doc.modelspace()
            
            # Анализируем все сущности
            for entity in msp:
                total_entities += 1
                entity_type = entity.dxftype()
                
                # Проверяем на проблемные типы сущностей
                if entity_type in self.PROBLEMATIC_ENTITY_TYPES:
                    problematic_entities += 1
                    issues.append(self._create_text_issue(entity, entity_type))
                
                # Проверяем толщину линий
                elif entity_type in ['LINE', 'LWPOLYLINE', 'POLYLINE', 'ARC', 'CIRCLE']:
                    thickness_issue = self._check_line_thickness(entity, entity_type)
                    if thickness_issue:
                        problematic_entities += 1
                        issues.append(thickness_issue)
                
                # Проверяем на непреобразованные полилинии
                elif entity_type == 'POLYLINE':
                    unconverted_issue = self._check_unconverted_polyline(entity)
                    if unconverted_issue:
                        problematic_entities += 1
                        issues.append(unconverted_issue)
                
                # Проверяем на незамкнутые контуры (КРИТИЧНО!)
                elif entity_type in ['LWPOLYLINE', 'POLYLINE', 'LINE', 'ARC']:
                    unclosed_issue = self._check_unclosed_contours(entity, entity_type)
                    if unclosed_issue:
                        problematic_entities += 1
                        issues.append(unclosed_issue)
            
            # Рассчитываем оценку готовности
            readiness_score = self._calculate_readiness_score(total_entities, problematic_entities, issues)
            is_ready = readiness_score >= 90.0  # 90% и выше - готов к резке
            
            return CuttingReadinessReport(
                filepath=filepath,
                filename=os.path.basename(filepath),
                is_ready=is_ready,
                issues=issues,
                total_entities=total_entities,
                problematic_entities=problematic_entities,
                readiness_score=readiness_score
            )
            
        except Exception as e:
            # Ошибка чтения файла
            issues.append(CuttingReadinessIssue(
                type='file_error',
                entity_type='FILE',
                description=f"Ошибка чтения файла: {str(e)}",
                recommendation="Проверьте целостность DXF файла",
                severity='error'
            ))
            
            return CuttingReadinessReport(
                filepath=filepath,
                filename=os.path.basename(filepath),
                is_ready=False,
                issues=issues,
                total_entities=0,
                problematic_entities=0,
                readiness_score=0.0
            )
    
    def _create_text_issue(self, entity, entity_type: str) -> CuttingReadinessIssue:
        """Создать проблему с текстовыми примитивами"""
        return CuttingReadinessIssue(
            type='text',
            entity_type=entity_type,
            description=f"Найден {entity_type}: '{getattr(entity, 'text', 'N/A')}' - не будет вырезан лазером",
            recommendation="Удалите текстовые элементы или преобразуйте их в контуры",
            severity='warning'
        )
    
    def _check_line_thickness(self, entity, entity_type: str) -> Optional[CuttingReadinessIssue]:
        """Проверить толщину линии"""
        try:
            # Получаем толщину линии
            thickness = getattr(entity.dxf, 'thickness', 0.0)
            
            if thickness > self.MAX_CUTTING_THICKNESS:
                return CuttingReadinessIssue(
                    type='thick_line',
                    entity_type=entity_type,
                    description=f"Линия толщиной {thickness:.2f}мм (макс. для резки: {self.MAX_CUTTING_THICKNESS}мм)",
                    recommendation="Установите толщину линии = 0 или удалите толстые линии",
                    severity='error'
                )
        except:
            pass
        
        return None
    
    def _check_unconverted_polyline(self, entity) -> Optional[CuttingReadinessIssue]:
        """Проверить на непреобразованные полилинии"""
        try:
            # Проверяем, является ли полилиния замкнутой и подходящей для резки
            if hasattr(entity, 'is_closed') and not entity.is_closed:
                return CuttingReadinessIssue(
                    type='unconverted_polyline',
                    entity_type='POLYLINE',
                    description="Незамкнутая полилиния - может быть проблематична для резки",
                    recommendation="Замкните полилинию или разбейте на отдельные линии",
                    severity='warning'
                )
        except:
            pass
        
        return None
    
    def _check_unclosed_contours(self, entity, entity_type: str) -> Optional[CuttingReadinessIssue]:
        """Проверить на незамкнутые контуры (КРИТИЧНО для резки!)"""
        try:
            # Проверяем полилинии
            if entity_type in ['LWPOLYLINE', 'POLYLINE']:
                is_closed = False
                
                if entity_type == 'LWPOLYLINE':
                    is_closed = getattr(entity, 'closed', False)
                elif entity_type == 'POLYLINE':
                    is_closed = getattr(entity, 'is_closed', False)
                
                if not is_closed:
                    return CuttingReadinessIssue(
                        type='unclosed_contour',
                        entity_type=entity_type,
                        description=f"Незамкнутая полилиния - КРИТИЧНО! Лазер не сможет вырезать",
                        recommendation="Замкните полилинию командой PEDIT или нарисуйте заново",
                        severity='error'
                    )
            
            # Проверяем отдельные линии и дуги (могут быть частью незамкнутого контура)
            elif entity_type in ['LINE', 'ARC']:
                # Для линий и дуг проверяем, есть ли они в составе незамкнутого контура
                # Это более сложная проверка, но для базового анализа достаточно
                pass
                
        except Exception as e:
            print(f"[DEBUG] Ошибка проверки незамкнутых контуров: {e}")
        
        return None
    
    def _calculate_readiness_score(self, total_entities: int, problematic_entities: int, issues: List[CuttingReadinessIssue]) -> float:
        """Рассчитать оценку готовности к резке (0-100%)"""
        if total_entities == 0:
            return 0.0
        
        # Базовый расчет
        base_score = ((total_entities - problematic_entities) / total_entities) * 100
        
        # Штрафы за критические проблемы
        critical_penalty = 0
        for issue in issues:
            if issue.severity == 'error':
                # Незамкнутые контуры - максимальный штраф
                if issue.type == 'unclosed_contour':
                    critical_penalty += 50  # Критично!
                else:
                    critical_penalty += 20
            elif issue.severity == 'warning':
                critical_penalty += 5
        
        final_score = max(0.0, base_score - critical_penalty)
        return min(100.0, final_score)
    
    def analyze_multiple_files(self, filepaths: List[str]) -> List[CuttingReadinessReport]:
        """Анализ нескольких файлов"""
        reports = []
        for filepath in filepaths:
            if os.path.exists(filepath):
                report = self.analyze_file(filepath)
                reports.append(report)
        return reports
    
    def get_summary_report(self, reports: List[CuttingReadinessReport]) -> Dict:
        """Получить сводный отчет по всем файлам"""
        total_files = len(reports)
        ready_files = sum(1 for r in reports if r.is_ready)
        total_issues = sum(len(r.issues) for r in reports)
        
        # Группируем проблемы по типам
        issue_types = {}
        for report in reports:
            for issue in report.issues:
                issue_type = issue.type
                if issue_type not in issue_types:
                    issue_types[issue_type] = 0
                issue_types[issue_type] += 1
        
        return {
            'total_files': total_files,
            'ready_files': ready_files,
            'not_ready_files': total_files - ready_files,
            'readiness_percentage': (ready_files / total_files * 100) if total_files > 0 else 0,
            'total_issues': total_issues,
            'issue_types': issue_types,
            'recommendations': self._generate_recommendations(issue_types)
        }
    
    def _generate_recommendations(self, issue_types: Dict[str, int]) -> List[str]:
        """Генерировать рекомендации на основе типов проблем"""
        recommendations = []
        
        if 'text' in issue_types:
            recommendations.append("Удалите или преобразуйте текстовые элементы в контуры")
        
        if 'thick_line' in issue_types:
            recommendations.append("Установите толщину всех линий = 0")
        
        if 'unconverted_polyline' in issue_types:
            recommendations.append("Проверьте и замкните все полилинии")
        
        if 'unclosed_contour' in issue_types:
            recommendations.append("КРИТИЧНО: Замкните все контуры - незамкнутые не вырезаются лазером!")
        
        if not recommendations:
            recommendations.append("Все файлы готовы к лазерной резке!")
        
        return recommendations

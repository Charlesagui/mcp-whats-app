#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de prueba para las funciones de búsqueda mejoradas
"""

from whatsapp import search_contacts, smart_search_contacts, calculate_similarity
import os

def test_similarity():
    """Prueba la función de similitud"""
    print("=== PRUEBAS DE SIMILITUD ===")
    
    test_cases = [
        ("juan", "juan", 1.0),
        ("juan", "juna", 0.75),  # transposición
        ("maria", "mria", 0.6),   # letra faltante
        ("carlos", "karlos", 0.83), # sustitución c->k
        ("alejandro", "alejandor", 0.89), # transposición final
        ("", "test", 0.0),        # string vacío
    ]
    
    for s1, s2, expected_min in test_cases:
        similarity = calculate_similarity(s1, s2)
        status = "OK" if similarity >= expected_min else "FAIL"
        print(f"{status} '{s1}' vs '{s2}': {similarity:.2f} (expected >= {expected_min})")

def test_search_functions():
    """Prueba las funciones de búsqueda si existe la base de datos"""
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'whatsapp-bridge', 'store', 'messages.db')
    
    if not os.path.exists(db_path):
        print(f"\n=== PRUEBAS DE BUSQUEDA ===")
        print(f"WARNING: Base de datos no encontrada en: {db_path}")
        print("   Inicia WhatsApp Bridge primero para crear la base de datos")
        return
    
    print(f"\n=== PRUEBAS DE BUSQUEDA ===")
    print(f"OK: Base de datos encontrada: {db_path}")
    
    # Pruebas con consultas de ejemplo
    test_queries = ["juan", "mar", "carlos", "test"]
    
    for query in test_queries:
        print(f"\n--- Busqueda: '{query}' ---")
        
        try:
            # Búsqueda básica
            basic_results = search_contacts(query, limit=5)
            print(f"Busqueda basica: {len(basic_results)} resultados")
            for contact in basic_results[:3]:
                print(f"  - {contact.name} ({contact.phone_number})")
            
            # Búsqueda inteligente
            smart_results = smart_search_contacts(query, limit=5, similarity_threshold=0.5)
            print(f"Busqueda inteligente: {len(smart_results)} resultados")
            for contact in smart_results[:3]:
                print(f"  - {contact.name} ({contact.phone_number})")
        except Exception as e:
            print(f"Error en busqueda '{query}': {e}")

if __name__ == "__main__":
    print("PROBANDO MEJORAS DE BUSQUEDA EN WHATSAPP MCP")
    print("=" * 50)
    
    # Prueba funciones de similitud
    test_similarity()
    
    # Prueba funciones de búsqueda
    test_search_functions()
    
    print("\n" + "=" * 50)
    print("Pruebas completadas")

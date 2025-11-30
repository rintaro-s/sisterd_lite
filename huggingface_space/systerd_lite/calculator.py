#!/usr/bin/env python3
"""
Calculator and complex numerical computation tools for systerd.
Provides mathematical operations, unit conversions, and scientific calculations.
"""

import math
import re
from decimal import Decimal, getcontext
from typing import Any, Dict, List, Union

# Set high precision for decimal calculations
getcontext().prec = 50


class Calculator:
    """Advanced calculator with support for complex expressions and unit conversions"""
    
    def __init__(self):
        self.constants = {
            'pi': math.pi,
            'e': math.e,
            'tau': math.tau,
            'phi': (1 + math.sqrt(5)) / 2,  # Golden ratio
            'c': 299792458,  # Speed of light (m/s)
            'h': 6.62607015e-34,  # Planck constant
            'G': 6.67430e-11,  # Gravitational constant
        }
        
        self.unit_conversions = {
            # Length
            'length': {
                'mm': 0.001, 'cm': 0.01, 'm': 1, 'km': 1000,
                'inch': 0.0254, 'ft': 0.3048, 'yard': 0.9144, 'mile': 1609.34,
            },
            # Weight
            'weight': {
                'mg': 0.000001, 'g': 0.001, 'kg': 1, 'ton': 1000,
                'oz': 0.0283495, 'lb': 0.453592,
            },
            # Temperature (special handling needed)
            'temperature': ['celsius', 'fahrenheit', 'kelvin'],
            # Data size
            'data': {
                'B': 1, 'KB': 1024, 'MB': 1024**2, 'GB': 1024**3,
                'TB': 1024**4, 'PB': 1024**5,
            },
            # Time
            'time': {
                'ms': 0.001, 's': 1, 'min': 60, 'hour': 3600,
                'day': 86400, 'week': 604800, 'year': 31536000,
            },
        }
    
    def evaluate(self, expression: str) -> Dict[str, Any]:
        """
        Evaluate a mathematical expression safely.
        Supports: +, -, *, /, **, sqrt, sin, cos, tan, log, ln, abs, etc.
        """
        try:
            # Replace constants
            for name, value in self.constants.items():
                expression = expression.replace(name, str(value))
            
            # Safe evaluation environment
            safe_dict = {
                '__builtins__': {},
                'abs': abs,
                'round': round,
                'min': min,
                'max': max,
                'sum': sum,
                'pow': pow,
                # Math functions
                'sqrt': math.sqrt,
                'sin': math.sin,
                'cos': math.cos,
                'tan': math.tan,
                'asin': math.asin,
                'acos': math.acos,
                'atan': math.atan,
                'sinh': math.sinh,
                'cosh': math.cosh,
                'tanh': math.tanh,
                'log': math.log10,
                'ln': math.log,
                'log2': math.log2,
                'exp': math.exp,
                'floor': math.floor,
                'ceil': math.ceil,
                'factorial': math.factorial,
                'gcd': math.gcd,
                'degrees': math.degrees,
                'radians': math.radians,
            }
            
            result = eval(expression, safe_dict)
            
            return {
                'status': 'ok',
                'expression': expression,
                'result': result,
                'type': type(result).__name__
            }
        
        except Exception as e:
            return {
                'status': 'error',
                'expression': expression,
                'error': str(e)
            }
    
    def convert_units(self, value: float, from_unit: str, to_unit: str,
                      category: str = None) -> Dict[str, Any]:
        """
        Convert between units.
        Auto-detects category if not specified.
        """
        try:
            # Auto-detect category
            if category is None:
                for cat, units in self.unit_conversions.items():
                    if cat == 'temperature':
                        if from_unit in units and to_unit in units:
                            category = cat
                            break
                    elif isinstance(units, dict):
                        if from_unit in units and to_unit in units:
                            category = cat
                            break
            
            if category is None:
                return {
                    'status': 'error',
                    'error': f'Could not determine category for {from_unit} -> {to_unit}'
                }
            
            # Special handling for temperature
            if category == 'temperature':
                result = self._convert_temperature(value, from_unit, to_unit)
            else:
                # Standard conversion via base unit
                units = self.unit_conversions[category]
                base_value = value * units[from_unit]
                result = base_value / units[to_unit]
            
            return {
                'status': 'ok',
                'value': value,
                'from_unit': from_unit,
                'to_unit': to_unit,
                'result': result,
                'category': category
            }
        
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def _convert_temperature(self, value: float, from_unit: str, to_unit: str) -> float:
        """Convert temperature between Celsius, Fahrenheit, and Kelvin"""
        # Convert to Celsius first
        if from_unit == 'celsius':
            celsius = value
        elif from_unit == 'fahrenheit':
            celsius = (value - 32) * 5/9
        elif from_unit == 'kelvin':
            celsius = value - 273.15
        else:
            raise ValueError(f'Unknown temperature unit: {from_unit}')
        
        # Convert from Celsius to target
        if to_unit == 'celsius':
            return celsius
        elif to_unit == 'fahrenheit':
            return celsius * 9/5 + 32
        elif to_unit == 'kelvin':
            return celsius + 273.15
        else:
            raise ValueError(f'Unknown temperature unit: {to_unit}')
    
    def matrix_operation(self, operation: str, matrix_a: List[List[float]],
                        matrix_b: List[List[float]] = None) -> Dict[str, Any]:
        """
        Perform matrix operations.
        Supported: add, subtract, multiply, transpose, determinant, inverse
        """
        try:
            import numpy as np
            
            a = np.array(matrix_a)
            
            if operation == 'transpose':
                result = a.T.tolist()
            
            elif operation == 'determinant':
                if a.shape[0] != a.shape[1]:
                    return {'status': 'error', 'error': 'Matrix must be square for determinant'}
                result = float(np.linalg.det(a))
            
            elif operation == 'inverse':
                if a.shape[0] != a.shape[1]:
                    return {'status': 'error', 'error': 'Matrix must be square for inverse'}
                result = np.linalg.inv(a).tolist()
            
            elif operation in ['add', 'subtract', 'multiply']:
                if matrix_b is None:
                    return {'status': 'error', 'error': f'{operation} requires two matrices'}
                
                b = np.array(matrix_b)
                
                if operation == 'add':
                    result = (a + b).tolist()
                elif operation == 'subtract':
                    result = (a - b).tolist()
                elif operation == 'multiply':
                    result = np.matmul(a, b).tolist()
            
            else:
                return {'status': 'error', 'error': f'Unknown operation: {operation}'}
            
            return {
                'status': 'ok',
                'operation': operation,
                'result': result
            }
        
        except ImportError:
            return {
                'status': 'error',
                'error': 'numpy not installed. Install with: pip install numpy'
            }
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def statistics(self, data: List[float]) -> Dict[str, Any]:
        """Calculate statistical measures"""
        try:
            import statistics as stats
            
            if not data:
                return {'status': 'error', 'error': 'Empty data list'}
            
            result = {
                'status': 'ok',
                'count': len(data),
                'sum': sum(data),
                'mean': stats.mean(data),
                'median': stats.median(data),
                'min': min(data),
                'max': max(data),
                'range': max(data) - min(data),
            }
            
            if len(data) >= 2:
                result['stdev'] = stats.stdev(data)
                result['variance'] = stats.variance(data)
            
            if len(set(data)) < len(data):
                try:
                    result['mode'] = stats.mode(data)
                except stats.StatisticsError:
                    result['mode'] = None
            
            return result
        
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def solve_equation(self, equation: str, variable: str = 'x') -> Dict[str, Any]:
        """
        Solve algebraic equations symbolically.
        Requires sympy library.
        """
        try:
            from sympy import symbols, Eq, solve
            from sympy.parsing.sympy_parser import parse_expr
            
            # Parse equation (format: "2*x + 3 = 7")
            if '=' in equation:
                left, right = equation.split('=')
                left = parse_expr(left.strip())
                right = parse_expr(right.strip())
                eq = Eq(left, right)
            else:
                # Assume equation equals zero
                eq = parse_expr(equation.strip())
            
            var = symbols(variable)
            solutions = solve(eq, var)
            
            return {
                'status': 'ok',
                'equation': equation,
                'variable': variable,
                'solutions': [float(s.evalf()) if hasattr(s, 'evalf') else str(s) for s in solutions]
            }
        
        except ImportError:
            return {
                'status': 'error',
                'error': 'sympy not installed. Install with: pip install sympy'
            }
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def base_conversion(self, number: str, from_base: int, to_base: int) -> Dict[str, Any]:
        """Convert numbers between different bases (2-36)"""
        try:
            if from_base < 2 or from_base > 36 or to_base < 2 or to_base > 36:
                return {
                    'status': 'error',
                    'error': 'Base must be between 2 and 36'
                }
            
            # Convert to decimal first
            decimal = int(number, from_base)
            
            # Convert to target base
            if to_base == 10:
                result = str(decimal)
            elif to_base == 2:
                result = bin(decimal)[2:]
            elif to_base == 8:
                result = oct(decimal)[2:]
            elif to_base == 16:
                result = hex(decimal)[2:].upper()
            else:
                # General base conversion
                digits = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
                result = ""
                n = decimal
                while n > 0:
                    result = digits[n % to_base] + result
                    n //= to_base
                if not result:
                    result = "0"
            
            return {
                'status': 'ok',
                'input': number,
                'from_base': from_base,
                'to_base': to_base,
                'result': result,
                'decimal_value': decimal
            }
        
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }

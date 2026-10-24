"""Instancia única del rate limiter (F2-02), en su propio módulo para que
tanto main.py (la registra en la app) como los endpoints públicos (la usan
como decorador) la importen sin crear un import circular entre ellos."""
from slowapi import Limiter

from infrastructure.utils.client_ip import ip_cliente

limiter = Limiter(key_func=ip_cliente)

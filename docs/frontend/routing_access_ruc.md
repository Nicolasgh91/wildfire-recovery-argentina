# Routing Access Matrix (RUC)

This document is the source of truth for route access behavior in the frontend.

## RUC Table

| ID | Caso de uso | Usuario invitado (no logueado) | Usuario logueado |
|---|---|---|---|
| RUC-01 | Accede a `/` | Accede a `/login` | Accede a `/home` |
| RUC-02 | Accede a `/login` | Ve landing/login | Ve landing/login |
| RUC-03 | Accede a `/register` | Ve registro | Ve registro |
| RUC-04 | Accede a `/home` | Ve Home | Ve Home |
| RUC-05 | Accede a `/map` | Ve mapa | Ve mapa |
| RUC-06 | Accede a `/exploracion` | Ve exploracion | Ve exploracion |
| RUC-07 | Accede a `/reports` | Redirige a `/exploracion` | Redirige a `/exploracion` |
| RUC-08 | Accede a `/fires/:id` | Ve detalle de incendio | Ve detalle de incendio |
| RUC-09 | Accede a `/faq`, `/manual`, `/glossary`, `/contact`, `/citizen-report` | Acceso directo | Acceso directo |
| RUC-10 | Accede a `/payments/return` | Ve "sesion requerida" y CTA a `/login` | Ve verificacion de pago |
| RUC-11 | Accede a `/audit`, `/credits`, `/profile`, `/fires/history` | Redirige a `/login` | Acceso permitido |
| RUC-12 | Accede a `/fires` | Redirige a `/fires/history` y luego a `/login` | Redirige a `/fires/history` |
| RUC-13 | Accede a `/certificates` o `/shelters` | Si feature flag ON: accede; si OFF: NotFound | Igual |
| RUC-14 | Accede a ruta inexistente (`*`) | NotFound | NotFound |

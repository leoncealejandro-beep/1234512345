# Telegram Store Bot

Bot de Telegram estilo tienda con menú, saldo, cupones, productos, referidos, perfil y admin básico.

## Instalación

```bash
cd telegram_store_bot
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

Edita `.env` y pega tu token de BotFather:

```env
BOT_TOKEN=TU_TOKEN
ADMIN_IDS=tu_id_de_telegram
```

## Ejecutar

```bash
python main.py
```

## Comandos

Usuario:
- `/start`
- `/menu`

Admin:
- `/admin`
- `/addbalance <telegram_id> <monto>`
- `/addcoupon <codigo> <monto> <usos>`
- `/addproduct <nombre> | <precio> | <stock separado por coma>`

Ejemplo:

```bash
/addbalance 123456789 10
/addcoupon FREE5 5 20
/addproduct Key Premium | 3.50 | KEY-AAA,KEY-BBB,KEY-CCC
```
"# 1234512345" 

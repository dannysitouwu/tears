- python3 -m venv tears
entrono virtual paera evitar conflicot con versiones y librerias


- source tears/bin/activate 
para activarlo y instalar todo en el entorno


- pip install '/'
para instalar librerias


- pip install "fastapi[standard-no-fastapi-cloud-cli]"
para instalar fastapi

- cd api
- docker-compose up on cd api
para correr api y dp



- uso de la libreria de ' argon2 ' 
solucion moderna para el hasshing, ya que no se debe de
guardar ese tipo de informacion valiosa del usuario en la db

- JWT



#! implementar cuando posible: refresh token - expires_in - scope

- python api/scripts/faker_populate.py --chats 5000 --members 5000 --messages 5000
para generar los datos 
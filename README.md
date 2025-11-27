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
#! arreglar el funcionamiento del elt (funciona, pero puede mejorar tanto en logica como msj de consola)

- python data/generator.py --min-users 0 --messages 0 --chats 0 --members 0 --messages 0
para generar los datos 
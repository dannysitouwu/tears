- python3 -m venv tears
entrono virtual paera evitar conflicot con versiones y librerias
(3.9.6)

- source tears/bin/activate 
para activarlo y instalar todo en el entorno


- cd api - pip install -r requirements.txt
para poder installar las dependencias exactas locales, para el correcto funconamiento

- requirements.in se mantiene como el original, con l adiferencia de .in en lugar de .txt para no renerar conflitos


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

min-users cantidad minima de usuarios en al db = --min-users 0 no creara nuevos usuarios si la db esta vacia o llena
--min-users 500
si la db posse 300 usuarios creados, creara los 200 que faltan

--messages 0
cantidad de mensajes por crear
si es 0 no se crea nada

--chats 0
cantidad de chats por crear
si es 0 no se crea nada

--members 0
en base a users N, repartira --members X en los chats existentes
- no crea nuevos usuarios o chats, apenas reasigna N cantidad de usuarios a los chats existentes -

--messages 0
cantiadd de mensajes por crear
si es 0 no se crea nada

- temporal server start-dev
para levantar el servicio de temporal

- cd temporal
python run_worker.py

-cd temporal
python run_workflow.py

http://localhost:3000/dashboard/3-tears-dashboard
# Currículum de Burócratas Mexicanos 

Python Script para descargar los cvs de los Funcionarios de México del portal Declaranet para el proyecto [Compranet](https://github.com/rsanchezavalos/compranet).

### Dependencies 

```
xvfbwrapper 
selenium
requests==2.13.0
beautifulsoup4 
numpy==1.11.2
boto==2.45.0
boto3==1.4.3
smart_open
```

### Configuration

Puedes tomar como input el [Directorio de funcionarios públicos del Gobierno Federal](https://datos.gob.mx/busca/dataset/directorio-de-funcionarios-publicos-del-gobierno-federal).

Utiliza este [Dockerfile](https://hub.docker.com/r/rsanchezavalos/python-headless-chromedriver/) para poder escalar el servicio en múltiples instancias.
# ETAPA 1: Construcción (Build)
FROM node:18-alpine as build

WORKDIR /app

# Copiamos solo el package.json primero para aprovechar el caché de Docker
COPY package.json package-lock.json ./
RUN npm install

# Copiamos el resto del código
COPY . .

# Construimos la app (genera la carpeta /dist)
RUN npm run build

# ETAPA 2: Servidor Web (Production)
# Usamos una imagen de Nginx súper liviana
FROM nginx:alpine

# Copiamos los archivos compilados de la Etapa 1 a la carpeta de Nginx
COPY --from=build /app/dist /usr/share/nginx/html

# Exponemos el puerto 80 (interno del contenedor)
EXPOSE 80

# Nginx corre solo en primer plano
CMD ["nginx", "-g", "daemon off;"]
# Build stage: Use Node to build the React app
FROM node:18 AS build
WORKDIR /app
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# Serve stage: Use Nginx to serve the static files
FROM nginx:alpine
COPY --from=build /app/build /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]

# ## Model File
# This service requires the `pose_landmarker_full.task` model file (not included in the repository).

# - Download the model from the official MediaPipe repository or your team's shared storage.
# - Place it in the `cv-service/` directory, next to `main.py`.
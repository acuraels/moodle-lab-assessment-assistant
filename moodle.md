# Запуск тестового Moodle для LTI 1.1

## 1. Клонирование репозитория
```bash
git clone https://github.com/infsys-lab/moodle-jupyterhub-docker.git
cd moodle-jupyterhub-docker
```

## 2. Правки docker-compose.yml
Замените образы в сервисах moodle и mariadb:
```yaml
  moodle:
    image: docker.io/bitnamilegacy/moodle:3
```
```yaml
  mariadb:
    image: docker.io/bitnamilegacy/mariadb:10.6
```
## 3. Правки jupyterhub/Dockerfile
Замените содержимое файла на следующее:

```dockerfile
ARG JUPYTERHUB_VERSION
FROM jupyterhub/jupyterhub-onbuild:$JUPYTERHUB_VERSION

RUN python3 -m pip install --no-cache-dir psycopg2-binary==2.9.1 \
    dockerspawner==12.1.0 jupyterhub-idle-culler==1.2.1 \
    jupyterhub-ltiauthenticator==1.3.0 \
    "pyOpenSSL>=23.2.0"

ENV LTI_KEY /srv/jupyterhub/secrets/lti.key
ENV LTI_SECRET /srv/jupyterhub/secrets/lti.secret
COPY ./secrets/lti.key "$LTI_KEY"
COPY ./secrets/lti.secret "$LTI_SECRET"
RUN chmod 700 /srv/jupyterhub/secrets && \
    chmod 600 /srv/jupyterhub/secrets/*

COPY ./secrets/admins /srv/jupyterhub/admins
```

## 4. Запуск (bash)
```bash
make build
docker network rm jupyterhub-network
docker-compose up -d
```

## 5. Вход в Moodle
URL: http://localhost

Логин: admin

Пароль: password

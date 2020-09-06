FROM python:3.8-slim-buster

ENV HOME=/home/revolut
ENV APP_HOME=$HOME/revolut-python
WORKDIR $APP_HOME

# Install project requirements
COPY requirements.txt $APP_HOME/requirements.txt
RUN pip install -r requirements.txt

# Copy the project
COPY . $APP_HOME

ENTRYPOINT ["python"]

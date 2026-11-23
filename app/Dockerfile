# Base image Mage: đã có pyodbc + ODBC Driver 18 (arm64/M1) + pandas + requests.
FROM mageai/mageai:0.9.79

RUN pip install --no-cache-dir streamlit

WORKDIR /home/src/app
EXPOSE 8501

# Code nằm ở volume /home/src; sửa .py chỉ cần `docker restart qa`.
CMD ["streamlit", "run", "qa_app.py", "--server.port=8501", "--server.address=0.0.0.0"]

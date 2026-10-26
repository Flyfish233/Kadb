/*
 * Copyright (c) 2021 mobile.dev inc.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 *
 */

package com.flyfishxu.kadb.queue

import com.flyfishxu.kadb.concurrent.BlockingLock
import com.flyfishxu.kadb.concurrent.startReaderThread
import com.flyfishxu.kadb.concurrent.withLock
import com.flyfishxu.kadb.core.AdbMessage
import com.flyfishxu.kadb.core.AdbProtocol
import com.flyfishxu.kadb.core.AdbReader
import com.flyfishxu.kadb.exception.AdbStreamClosed
import kotlin.concurrent.Volatile
import okio.IOException

/** One transport reader detects EOF even when all streams are idle. */
internal class AdbMessageQueue(
    private val reader: AdbReader,
    private val closeUnknownStream: (localId: Int, remoteId: Int) -> Unit = { _, _ -> },
    private val closeTransport: () -> Unit,
) : AutoCloseable {
    private val lock = BlockingLock()
    private val changed = lock.newCondition()
    private val queues = mutableMapOf<Int, MutableMap<Int, ArrayDeque<AdbMessage>>>()
    private val openStreams = mutableSetOf<Int>()
    private val openingStreams = mutableMapOf<Int, Int?>()
    // First OKAY binds the peer for this local ID until the stream is removed.
    private val remoteIds = mutableMapOf<Int, Int>()
    private var nextLocalId = 1u
    @Volatile private var failure: Throwable? = null
    val isOpen: Boolean get() = failure == null

    init {
        startReaderThread {
            try {
                while (isOpen) dispatch(reader.readMessage())
            } catch (error: Throwable) {
                terminate(error)
            } finally {
                runCatching { reader.close() }
            }
        }
    }

    fun take(localId: Int, command: Int): AdbMessage = lock.withLock {
        while (true) {
            val stream = queues[localId] ?: throw AdbStreamClosed(localId)
            stream[command]?.removeFirstOrNull()?.let { return it }
            if (localId !in openStreams) throw AdbStreamClosed(localId)
            failure?.let { throw it }
            changed.await()
        }
        @Suppress("UNREACHABLE_CODE") error("Unreachable")
    }

    fun startListening(localId: Int) = startListening(localId, remoteId = null)

    /** Used by direct stream fixtures; production OPEN learns its remote ID from OKAY. */
    fun startListening(localId: Int, remoteId: Int?) = lock.withLock {
        require(localId != 0 && remoteId != 0) { "ADB stream IDs must be nonzero" }
        failure?.let { throw it }
        openStreams.add(localId)
        queues.getOrPut(localId) { mutableMapOf() }
        if (remoteId != null) remoteIds[localId] = remoteId
        Unit
    }

    /** Never reuse an ID within a connection: late replies must not attach to a later OPEN. */
    fun startOpening(): Int = lock.withLock {
        failure?.let { throw it }
        while (true) {
            if (nextLocalId == 0u) throw IOException("ADB stream IDs exhausted; reset the connection")
            val localId = nextLocalId++.toInt()
            if (localId in queues) continue
            openStreams.add(localId)
            queues[localId] = mutableMapOf()
            openingStreams[localId] = null
            return localId
        }
        @Suppress("UNREACHABLE_CODE") error("Unreachable")
    }

    fun cancelOpening(localId: Int) = lock.withLock {
        if (localId in openingStreams) {
            openStreams.remove(localId)
            queues.remove(localId)
            remoteIds.remove(localId)
            changed.signalAll()
        }
    }

    /** Transfer a pending OPEN to AdbStream, unless cancellation already removed its queue. */
    fun finishOpening(localId: Int): Boolean = lock.withLock {
        if (localId !in openingStreams || localId !in queues) return false
        openingStreams.remove(localId)
        true
    }

    /** Return an already received remote ID so failed/cancelled OPEN can send its CLSE. */
    fun abandonOpening(localId: Int): Int? = lock.withLock {
        val remoteId = openingStreams.remove(localId)
        openStreams.remove(localId)
        queues.remove(localId)
        remoteIds.remove(localId)
        changed.signalAll()
        remoteId
    }

    fun stopListening(localId: Int) = lock.withLock {
        openStreams.remove(localId)
        queues.remove(localId)
        remoteIds.remove(localId)
        changed.signalAll()
    }

    private fun dispatch(message: AdbMessage) {
        val lateOkay = lock.withLock {
            val localId = message.arg1
            if (localId == 0) return@withLock false
            val stream = queues[localId]
            val remoteId = remoteIds[localId]
            // Match AOSP handle_packet: OKAY/WRTE require both IDs and established
            // traffic must belong to the peer selected by the first OKAY.
            // CLSE(0, local) remains valid for old adbd versions on this same transport.
            when (message.command) {
                AdbProtocol.CMD_OKAY -> {
                    if (message.arg0 == 0) return@withLock false
                    if (stream == null) return@withLock true
                    if (localId !in openStreams || remoteId != null && remoteId != message.arg0) {
                        return@withLock false
                    }
                    if (remoteId == null) {
                        remoteIds[localId] = message.arg0
                        if (localId in openingStreams) openingStreams[localId] = message.arg0
                    }
                    stream.getOrPut(message.command) { ArrayDeque() }.add(message)
                }
                AdbProtocol.CMD_WRTE -> {
                    if (stream == null || localId !in openStreams || remoteId != message.arg0) {
                        return@withLock false
                    }
                    stream.getOrPut(message.command) { ArrayDeque() }.add(message)
                }
                AdbProtocol.CMD_CLSE -> {
                    if (stream == null || message.arg0 != 0 && remoteId != message.arg0) {
                        return@withLock false
                    }
                    openStreams.remove(localId)
                }
                else -> return@withLock false
            }
            changed.signalAll()
            false
        }
        // AOSP reclaims the remote service when the local OPEN owner has already gone away.
        // Never perform transport I/O under the queue lock: other streams must still drain.
        // https://android.googlesource.com/platform/packages/modules/adb/+/1cf2f017d312f73b3dc53bda85ef2610e35a80e9/adb.cpp#590
        if (lateOkay) closeUnknownStream(message.arg1, message.arg0)
    }

    private fun terminate(error: Throwable) {
        lock.withLock {
            if (failure != null) return
            failure = error
            changed.signalAll()
        }
        // Close the socket before any buffered reader/writer: unblock pending I/O first.
        runCatching { closeTransport() }
    }

    override fun close() = terminate(IOException("ADB connection closed"))

    fun ensureEmpty() = lock.withLock {
        check(queues.isEmpty() && openStreams.isEmpty() && openingStreams.isEmpty() && remoteIds.isEmpty()) {
            "ADB streams still open: ${queues.keys}; pending OPENs: ${openingStreams.keys}"
        }
    }
}

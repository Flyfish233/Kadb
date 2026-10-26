@file:OptIn(kotlin.ExperimentalMultiplatform::class)

package com.flyfishxu.kadb.exception

import kotlin.OptionalExpectation
import kotlin.reflect.KClass

/** Export recoverable failures as NSError without adding checked exceptions to the Java API. */
@Target(AnnotationTarget.FUNCTION)
@Retention(AnnotationRetention.BINARY)
@OptionalExpectation
internal expect annotation class NativeThrows(vararg val exceptionClasses: KClass<out Throwable>)

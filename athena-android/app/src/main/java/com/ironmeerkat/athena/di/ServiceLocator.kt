package com.ironmeerkat.athena.di

import athena.sdk.policy.AthenaDevicePolicyClient
import athena.sdk.policy.DevicePolicyClient

object ServiceLocator {
  val devicePolicyClient: DevicePolicyClient by lazy { AthenaDevicePolicyClient() }
}



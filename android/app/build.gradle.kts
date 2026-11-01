plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("org.jetbrains.kotlin.plugin.compose")
}

val releaseTag = providers.environmentVariable("PASSWORD_GENERATOR_RELEASE_TAG")
    .orNull?.takeIf { it.isNotBlank() }
val releaseParts = releaseTag?.let {
    val match = Regex("""v(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)""").matchEntire(it)
        ?: error("Release tag must be vMAJOR.MINOR.PATCH")
    match.groupValues.drop(1).map(String::toLong).also { parts ->
        require(parts[1] < 1000 && parts[2] < 1000)
        require(parts[0] <= 2100)
        require(parts[0] * 1000000 + parts[1] * 1000 + parts[2] in 1..2100000000)
    }
}
val signingValues = listOf("ANDROID_KEYSTORE_PATH", "ANDROID_KEYSTORE_PASSWORD",
    "ANDROID_KEY_ALIAS", "ANDROID_KEY_PASSWORD").associateWith { System.getenv(it) }
val hasSigning = signingValues.values.all { !it.isNullOrBlank() }
if (gradle.startParameter.taskNames.any { it.contains("Release", ignoreCase = true) }) {
    require(hasSigning) { "Release APK requires all ANDROID signing environment variables." }
    require(releaseParts != null) { "Release APK requires PASSWORD_GENERATOR_RELEASE_TAG." }
}

// Also guard aggregate tasks such as "assemble" and "build".
gradle.taskGraph.whenReady {
    if (allTasks.any { it.project == project && it.name in setOf("assembleRelease", "bundleRelease", "packageRelease") }) {
        require(hasSigning) { "Release APK requires all ANDROID signing environment variables." }
        require(releaseParts != null) { "Release APK requires PASSWORD_GENERATOR_RELEASE_TAG." }
    }
}

android {
    namespace = "pl.franek.passwordgenerator"
    compileSdk = 35

    defaultConfig {
        applicationId = "pl.franek.passwordgenerator"
        minSdk = 26
        targetSdk = 35
        versionCode = releaseParts?.let { (it[0] * 1000000 + it[1] * 1000 + it[2]).toInt() } ?: 1
        versionName = releaseTag?.removePrefix("v") ?: "development"

        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
    }

    signingConfigs {
        if (hasSigning) {
            create("distribution") {
                storeType = "PKCS12"
                storeFile = file(signingValues.getValue("ANDROID_KEYSTORE_PATH")!!)
                storePassword = signingValues.getValue("ANDROID_KEYSTORE_PASSWORD")
                keyAlias = signingValues.getValue("ANDROID_KEY_ALIAS")
                keyPassword = signingValues.getValue("ANDROID_KEY_PASSWORD")
            }
        }
    }
    buildTypes {
        getByName("release") {
            if (hasSigning) signingConfig = signingConfigs.getByName("distribution")
        }
    }

    sourceSets.getByName("test").resources.srcDir("../../tests/fixtures")

    buildFeatures {
        compose = true
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    kotlinOptions {
        jvmTarget = "17"
    }

    packaging {
        resources.excludes += "/META-INF/{AL2.0,LGPL2.1}"
    }
}

dependencies {
    implementation(platform("androidx.compose:compose-bom:2024.12.01"))
    implementation("androidx.activity:activity-compose:1.10.0")
    implementation("androidx.compose.material3:material3")
    implementation("androidx.compose.ui:ui")
    implementation("androidx.compose.ui:ui-tooling-preview")
    implementation("androidx.lifecycle:lifecycle-viewmodel-compose:2.8.7")

    debugImplementation("androidx.compose.ui:ui-tooling")
    testImplementation("junit:junit:4.13.2")
    testImplementation("org.json:json:20240303")
    androidTestImplementation(platform("androidx.compose:compose-bom:2024.12.01"))
    androidTestImplementation("androidx.test:runner:1.6.2")
    androidTestImplementation("androidx.test.ext:junit:1.2.1")
    androidTestImplementation("androidx.compose.ui:ui-test-junit4")
}

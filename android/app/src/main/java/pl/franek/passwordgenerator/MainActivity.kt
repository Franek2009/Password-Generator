package pl.franek.passwordgenerator

import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.net.Uri
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.text.selection.SelectionContainer
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Checkbox
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedCard
import androidx.compose.material3.Slider
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import kotlinx.coroutines.launch

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent { PasswordGeneratorApp() }
    }
}

private val Dark = Color(0xFF18181B)
private val Card = Color(0xFF27272A)
private val TextPrimary = Color(0xFFFAFAFA)
private val TextSecondary = Color(0xFFA1A1AA)

@Composable
fun PasswordGeneratorApp() {
    MaterialTheme {
        Surface(modifier = Modifier.fillMaxSize(), color = Dark) {
            GeneratorScreen()
        }
    }
}

@Composable
private fun GeneratorScreen() {
    val context = LocalContext.current
    val generator = remember { PasswordGenerator() }
    val scope = rememberCoroutineScope()
    val snackbar = remember { SnackbarHostState() }
    var mode by remember { mutableStateOf(PasswordMode.MANAGER) }
    var length by remember { mutableStateOf(20) }
    var words by remember { mutableStateOf(3) }
    var uppercase by remember { mutableStateOf(true) }
    var lowercase by remember { mutableStateOf(true) }
    var numbers by remember { mutableStateOf(true) }
    var special by remember { mutableStateOf(true) }
    var separator by remember { mutableStateOf("-") }
    var password by remember { mutableStateOf("") }
    var customWords by remember { mutableStateOf<List<String>?>(null) }
    var customName by remember { mutableStateOf<String?>(null) }

    val wordListPicker = rememberLauncherForActivityResult(
        ActivityResultContracts.OpenDocument(),
    ) { uri: Uri? ->
        if (uri != null) {
            runCatching { readWords(context, uri) }
                .onSuccess {
                    customWords = it
                    customName = uri.lastPathSegment ?: "własna lista"
                }
                .onFailure { scope.launch { snackbar.showSnackbar(it.message ?: "Nie można odczytać pliku.") } }
        }
    }

    Column(
        modifier = Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(24.dp),
        verticalArrangement = Arrangement.spacedBy(14.dp),
    ) {
        Text("Password Generator", color = TextPrimary, fontSize = 28.sp)
        Text("Twórz bezpieczne hasła z łatwością", color = TextSecondary)
        Label("TRYB")
        ChoiceMenu(
            value = if (mode == PasswordMode.MANAGER) "Menedżer haseł" else "Czytelne hasło",
            values = listOf("Menedżer haseł", "Czytelne hasło"),
            onSelected = { mode = if (it == "Menedżer haseł") PasswordMode.MANAGER else PasswordMode.HUMAN },
        )

        if (mode == PasswordMode.MANAGER) {
            SettingHeader("Długość", length.toString())
            Slider(value = length.toFloat(), onValueChange = { length = it.toInt() }, valueRange = 8f..64f, steps = 55)
            CheckOption("Wielkie litery", uppercase) { uppercase = it }
            CheckOption("Małe litery", lowercase) { lowercase = it }
            CheckOption("Cyfry", numbers) { numbers = it }
            CheckOption("Znaki specjalne", special) { special = it }
        } else {
            SettingHeader("Liczba słów", words.toString())
            Slider(value = words.toFloat(), onValueChange = { words = it.toInt() }, valueRange = 2f..8f, steps = 5)
            Text("Separator", color = TextPrimary)
            ChoiceMenu(separator, PasswordGenerator.SEPARATORS + "Random") { separator = it }
            CheckOption("Cyfry", numbers) { numbers = it }
            CheckOption("Znaki specjalne", special) { special = it }
            OutlinedButton(onClick = { wordListPicker.launch(arrayOf("text/plain")) }, modifier = Modifier.fillMaxWidth()) {
                Text(customName?.let { "Lista: $it" } ?: "Wybierz własną listę słów")
            }
            if (customWords != null) {
                OutlinedButton(onClick = { customWords = null; customName = null }, modifier = Modifier.fillMaxWidth()) {
                    Text("Użyj wbudowanej polskiej listy")
                }
            }
        }

        Label("WYGENEROWANE HASŁO")
        OutlinedCard(modifier = Modifier.fillMaxWidth()) {
            SelectionContainer {
                Text(password.ifBlank { "Hasło pojawi się tutaj" }, color = if (password.isBlank()) TextSecondary else TextPrimary, modifier = Modifier.background(Card).fillMaxWidth().padding(16.dp))
            }
        }
        Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
            Button(
                onClick = {
                    val config = PasswordConfig(mode, length, uppercase, lowercase, numbers, special, words, separator)
                    runCatching {
                        val activeWords = customWords ?: if (mode == PasswordMode.HUMAN) loadBuiltInWords(context) else emptyList()
                        generator.generate(config, activeWords)
                    }.onSuccess { password = it }
                        .onFailure { scope.launch { snackbar.showSnackbar(it.message ?: "Nie udało się wygenerować hasła.") } }
                },
                modifier = Modifier.weight(2f),
                colors = ButtonDefaults.buttonColors(containerColor = TextPrimary, contentColor = Dark),
            ) { Text("Generuj") }
            OutlinedButton(
                onClick = {
                    if (password.isNotBlank()) {
                        val clipboard = context.getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
                        clipboard.setPrimaryClip(ClipData.newPlainText("password", password))
                        scope.launch { snackbar.showSnackbar("Skopiowano hasło") }
                    }
                },
                modifier = Modifier.weight(1f),
            ) { Text("Kopiuj") }
        }
        Spacer(Modifier.height(4.dp))
        SnackbarHost(snackbar)
    }
}

@Composable
private fun Label(text: String) = Text(text, color = TextSecondary, fontSize = 11.sp)

@Composable
private fun SettingHeader(label: String, value: String) {
    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
        Text(label, color = TextPrimary)
        Text(value, color = TextPrimary)
    }
}

@Composable
private fun CheckOption(label: String, checked: Boolean, onChanged: (Boolean) -> Unit) {
    Row(verticalAlignment = Alignment.CenterVertically) {
        Checkbox(checked, onChanged)
        Text(label, color = TextPrimary)
    }
}

@Composable
private fun ChoiceMenu(value: String, values: List<String>, onSelected: (String) -> Unit) {
    var expanded by remember { mutableStateOf(false) }
    Column {
        OutlinedButton(onClick = { expanded = true }, modifier = Modifier.fillMaxWidth()) { Text(value) }
        DropdownMenu(expanded = expanded, onDismissRequest = { expanded = false }) {
            values.forEach { option ->
                DropdownMenuItem(text = { Text(option) }, onClick = { onSelected(option); expanded = false })
            }
        }
    }
}

private fun loadBuiltInWords(context: Context): List<String> =
    context.assets.open("words.txt").bufferedReader(Charsets.UTF_8).use { reader ->
        reader.lineSequence().map { it.trim() }.filter { it.isNotEmpty() }.toList()
    }

private fun readWords(context: Context, uri: Uri): List<String> {
    val words = context.contentResolver.openInputStream(uri)?.bufferedReader(Charsets.UTF_8)?.use { reader ->
        reader.lineSequence().map { it.trim() }.filter { it.isNotEmpty() }.toList()
    } ?: error("Nie można otworzyć listy słów.")
    require(words.isNotEmpty()) { "Lista słów nie może być pusta." }
    return words
}

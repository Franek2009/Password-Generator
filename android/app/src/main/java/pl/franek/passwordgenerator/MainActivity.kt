package pl.franek.passwordgenerator

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.compose.BackHandler
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.selection.toggleable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.SolidColor
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.graphics.vector.PathParser
import androidx.compose.ui.graphics.vector.rememberVectorPainter
import androidx.compose.ui.focus.onFocusChanged
import androidx.compose.ui.platform.LocalFocusManager
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.core.view.WindowCompat
import androidx.lifecycle.viewmodel.compose.viewModel
import kotlinx.coroutines.launch

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent { PasswordGeneratorApp() }
    }
}

@Composable
fun PasswordGeneratorApp(model: GeneratorViewModel = viewModel()) {
    val context = LocalContext.current
    val ui = remember { SharedUi(context) }
    val state = model.state
    val dark = when (state.theme) { "dark" -> true; "light" -> false; else -> isSystemInDarkTheme() }
    val palette = ui.palette(dark)
    fun color(key: String) = Color(android.graphics.Color.parseColor(palette.getString(key)))
    val colors = if (dark) darkColorScheme(
        primary = color("accent"), onPrimary = color("background"), background = color("background"),
        surface = color("surface"), onSurface = color("text"), onBackground = color("text"),
        onSurfaceVariant = color("muted"), outline = color("border"), surfaceVariant = color("surface"),
    ) else lightColorScheme(
        primary = color("accent"), onPrimary = color("background"), background = color("background"),
        surface = color("surface"), onSurface = color("text"), onBackground = color("text"),
        onSurfaceVariant = color("muted"), outline = color("border"), surfaceVariant = color("surface"),
    )
    SideEffect {
        val window = (context as? ComponentActivity)?.window
        if (window != null) {
            window.statusBarColor = android.graphics.Color.parseColor(palette.getString("background"))
            window.navigationBarColor = android.graphics.Color.parseColor(palette.getString("background"))
            WindowCompat.getInsetsController(window, window.decorView).apply {
                isAppearanceLightStatusBars = !dark
                isAppearanceLightNavigationBars = !dark
            }
        }
    }
    MaterialTheme(colorScheme = colors, shapes = Shapes(small = RoundedCornerShape(6.dp), medium = RoundedCornerShape(8.dp))) {
        var settings by rememberSaveable { mutableStateOf(false) }
        var about by rememberSaveable { mutableStateOf(false) }
        val snackbar = remember { SnackbarHostState() }
        val t: (String) -> String = { ui.text(state.language, it) }
        LaunchedEffect(model.message, state.language) {
            model.message?.let { key ->
                snackbar.showSnackbar(t(key))
                model.clearMessage()
            }
        }
        BackHandler(enabled = settings) { settings = false }
        Scaffold(containerColor = colors.background, contentWindowInsets = WindowInsets.safeDrawing,
            snackbarHost = { SnackbarHost(snackbar) }) { padding ->
            Column(Modifier.fillMaxSize().padding(padding).verticalScroll(rememberScrollState()).padding(horizontal = 20.dp, vertical = 12.dp),
                verticalArrangement = Arrangement.spacedBy(12.dp)) {
                Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
                    if (settings) {
                        IconButton(onClick = { settings = false }) { SharedIcon(ui, "back", t("back")) }
                        Text(t("settings"), style = MaterialTheme.typography.titleLarge)
                    } else {
                        Image(painterResource(R.drawable.app_icon), null, Modifier.size(30.dp).clip(CircleShape))
                        Spacer(Modifier.width(10.dp))
                        Text("Password Generator", Modifier.weight(1f), fontSize = 18.sp, fontWeight = FontWeight.Medium)
                        var expanded by remember { mutableStateOf(false) }
                        Box {
                            IconButton(onClick = { expanded = true }) { SharedIcon(ui, "more", t("more")) }
                            DropdownMenu(expanded, { expanded = false }) {
                                DropdownMenuItem(text = { Text(t("settings")) }, onClick = { expanded = false; settings = true })
                                DropdownMenuItem(text = { Text(t("about")) }, onClick = { expanded = false; about = true })
                            }
                        }
                    }
                }
                if (settings) {
                    SettingsScreen(state, model, t)
                } else {
                    GeneratorScreen(ui, state, model, t, color("button"), color("button_text"))
                }
            }
        }
        if (about) AlertDialog(onDismissRequest = { about = false },
            title = { Text(t("about")) },
            text = { Text("Password Generator ${context.packageManager.getPackageInfo(context.packageName, 0).versionName}\n\n${t("about_text")}") },
            confirmButton = { TextButton(onClick = { about = false }) { Text(t("close")) } })
    }
}

@Composable
private fun SharedIcon(ui: SharedUi, name: String, description: String) {
    val vector = remember(name) {
        ImageVector.Builder(name, 24.dp, 24.dp, 24f, 24f).apply {
            addPath(PathParser().parsePathString(ui.path(name)).toNodes(),
                fill = null, stroke = SolidColor(Color.Black), strokeLineWidth = 1.8f)
        }.build()
    }
    Icon(rememberVectorPainter(vector), description, Modifier.size(24.dp))
}

@Composable
private fun GeneratorScreen(ui: SharedUi, state: UiState, model: GeneratorViewModel, t: (String) -> String, button: Color, buttonText: Color) {
    val human = state.mode == PasswordMode.HUMAN
    val picker = rememberLauncherForActivityResult(ActivityResultContracts.OpenDocument()) { uri ->
        uri?.let { model.chooseWordlist(it) }
    }
    TabRow(selectedTabIndex = if (human) 1 else 0, containerColor = MaterialTheme.colorScheme.background) {
        listOf("random", "phrase").forEachIndexed { index, key ->
            Tab(selected = human == (index == 1), onClick = { model.update { it.copy(mode = if (index == 0) PasswordMode.MANAGER else PasswordMode.HUMAN) } },
                text = { Text(t(key), maxLines = 2) })
        }
    }
    OutlinedCard(shape = RoundedCornerShape(8.dp), colors = CardDefaults.outlinedCardColors(containerColor = MaterialTheme.colorScheme.surface)) {
        Row(Modifier.fillMaxWidth().padding(start = 12.dp, end = 4.dp, top = 4.dp, bottom = 4.dp), verticalAlignment = Alignment.CenterVertically) {
            OutlinedTextField(value = state.password, onValueChange = {}, readOnly = true, singleLine = true,
                placeholder = { Text(t("placeholder"), fontSize = 14.sp) },
                textStyle = LocalTextStyle.current.copy(fontFamily = FontFamily.Monospace, fontSize = 20.sp),
                modifier = Modifier.weight(1f).semantics { contentDescription = t("placeholder") },
                colors = OutlinedTextFieldDefaults.colors(focusedBorderColor = Color.Transparent, unfocusedBorderColor = Color.Transparent))
            IconButton(enabled = state.password.isNotEmpty(), onClick = model::copy) { SharedIcon(ui, "copy", t("copy")) }
        }
    }
    NumberSetting(if (human) t("words") else t("length"), if (human) state.words else state.length,
        if (human) 2..8 else 8..64) { number -> model.update { if (human) it.copy(words = number) else it.copy(length = number) } }
    if (human) {
        Choice(t("separator"), state.separator, PasswordGenerator.SEPARATORS + "Random",
            { when(it) { " " -> t("space"); "Random" -> t("random_separator"); else -> it } }) { value -> model.update { it.copy(separator = value) } }
        Choice(t("wordlist"), if (state.wordlist.isEmpty()) "builtin" else "selected",
            if (state.wordlist.isEmpty()) listOf("builtin", "custom") else listOf("builtin", "selected", "custom"),
            { when(it) { "builtin" -> t("builtin"); "selected" -> state.wordlistName; else -> t("custom") } }, enabled = !model.working) {
                when(it) { "builtin" -> model.useBuiltIn(); "custom" -> picker.launch(arrayOf("text/plain")) }
            }
    } else {
        CheckOption(t("uppercase"), state.uppercase) { value -> model.update { it.copy(uppercase = value) } }
        CheckOption(t("lowercase"), state.lowercase) { value -> model.update { it.copy(lowercase = value) } }
    }
    CheckOption(t("numbers"), if (human) state.humanNumbers else state.managerNumbers) { value ->
        model.update { if (human) it.copy(humanNumbers = value) else it.copy(managerNumbers = value) }
    }
    CheckOption(t("symbols"), if (human) state.humanSpecial else state.managerSpecial) { value ->
        model.update { if (human) it.copy(humanSpecial = value) else it.copy(managerSpecial = value) }
    }
    HorizontalDivider(color = MaterialTheme.colorScheme.outline)
    Button(onClick = model::generate, enabled = !model.working, modifier = Modifier.fillMaxWidth().heightIn(min = 48.dp),
        shape = RoundedCornerShape(7.dp), colors = ButtonDefaults.buttonColors(containerColor = button, contentColor = buttonText)) {
        Text(t("generate"), fontSize = 17.sp, modifier = Modifier.padding(vertical = 4.dp))
    }
}

@Composable
private fun NumberSetting(label: String, value: Int, range: IntRange, onChange: (Int) -> Unit) {
    val focus = LocalFocusManager.current
    var input by remember(value) { mutableStateOf(value.toString()) }
    Column {
        Text("$label: $value", style = MaterialTheme.typography.bodyMedium)
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp)) {
            Slider(value.toFloat(), { onChange(it.toInt()) }, modifier = Modifier.weight(1f).semantics { contentDescription = label },
                valueRange = range.first.toFloat()..range.last.toFloat(), steps = range.last - range.first - 1)
            OutlinedTextField(input, { raw ->
                if (raw.length <= 2 && raw.all(Char::isDigit)) {
                    input = raw
                    raw.toIntOrNull()?.takeIf { it in range }?.let(onChange)
                }
            }, singleLine = true, modifier = Modifier.width(72.dp).onFocusChanged { if (!it.isFocused) input = value.toString() }.semantics { contentDescription = label },
                isError = input.toIntOrNull()?.let { it !in range } ?: true,
                keyboardActions = KeyboardActions(onDone = { focus.clearFocus() }),
                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number))
        }
    }
}

@Composable
private fun CheckOption(label: String, checked: Boolean, onChanged: (Boolean) -> Unit) {
    Row(Modifier.fillMaxWidth().heightIn(min = 48.dp).toggleable(value = checked, role = Role.Checkbox, onValueChange = onChanged),
        verticalAlignment = Alignment.CenterVertically) {
        Checkbox(checked, null)
        Spacer(Modifier.width(8.dp))
        Text(label)
    }
}

@Composable
private fun Choice(label: String, value: String, choices: List<String>, display: (String) -> String,
                   enabled: Boolean = true, onSelected: (String) -> Unit) {
    var expanded by remember { mutableStateOf(false) }
    Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
        Text(label, color = MaterialTheme.colorScheme.onSurfaceVariant, style = MaterialTheme.typography.bodyMedium)
        Box {
            OutlinedButton(onClick = { expanded = true }, enabled = enabled, modifier = Modifier.fillMaxWidth().heightIn(min = 48.dp),
                shape = RoundedCornerShape(6.dp)) { Text(display(value), Modifier.weight(1f)); Text("⌄") }
            DropdownMenu(expanded, { expanded = false }) {
                choices.forEach { choice -> DropdownMenuItem(text = { Text(display(choice)) },
                    onClick = { onSelected(choice); expanded = false }) }
            }
        }
    }
}

@Composable
private fun SettingsScreen(state: UiState, model: GeneratorViewModel, t: (String) -> String) {
    Text(t("general"), style = MaterialTheme.typography.titleMedium)
    Surface(shape = RoundedCornerShape(8.dp)) {
        Row(Modifier.fillMaxWidth().padding(12.dp), verticalAlignment = Alignment.CenterVertically) {
            Text(t("auto_copy"), Modifier.weight(1f))
            Switch(state.autoCopy, { value -> model.update { it.copy(autoCopy = value) } }, Modifier.semantics { contentDescription = t("auto_copy") })
        }
    }
    Text(t("appearance"), style = MaterialTheme.typography.titleMedium)
    Choice(t("theme"), state.theme, listOf("system", "light", "dark"), { t(it) }) { value -> model.update { it.copy(theme = value) } }
    Choice(t("language"), state.language, listOf("system", "pl", "en"), { when(it) { "pl" -> "Polski"; "en" -> "English"; else -> t(it) } }) {
        value -> model.update { it.copy(language = value) }
    }
}

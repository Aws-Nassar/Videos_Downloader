package com.mediaflow.android;

import android.Manifest;
import android.app.Activity;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.content.pm.PackageManager;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.media.MediaScannerConnection;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.os.Environment;
import android.provider.Settings;
import android.view.Gravity;
import android.view.View;
import android.view.ViewGroup;
import android.widget.ArrayAdapter;
import android.widget.Button;
import android.widget.CheckBox;
import android.widget.EditText;
import android.widget.FrameLayout;
import android.widget.ImageView;
import android.widget.LinearLayout;
import android.widget.ProgressBar;
import android.widget.RadioButton;
import android.widget.RadioGroup;
import android.widget.ScrollView;
import android.widget.Spinner;
import android.widget.TextView;
import android.widget.Toast;

import androidx.core.content.FileProvider;

import com.chaquo.python.PyObject;
import com.chaquo.python.Python;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.File;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public class MainActivity extends Activity {
    private int BG;
    private int PANEL;
    private int CARD;
    private int INPUT;
    private int TEXT;
    private int MUTED;
    private int ACCENT = Color.rgb(43, 125, 233);
    private int DANGER = Color.rgb(244, 63, 94);

    private final ExecutorService executor = Executors.newSingleThreadExecutor();
    private PyObject backend;
    private EditText urlEdit;
    private ImageView thumbImage;
    private TextView infoTitle;
    private TextView infoMeta;
    private TextView statusText;
    private TextView speedText;
    private TextView logText;
    private ProgressBar progressBar;
    private RadioButton videoRadio;
    private RadioButton audioRadio;
    private Spinner formatSpinner;
    private Spinner qualitySpinner;
    private CheckBox playlistCheck;
    private CheckBox subsCheck;
    private CheckBox thumbCheck;
    private CheckBox sponsorCheck;
    private Button downloadButton;
    private Button cancelButton;
    private List<String> videoFormats = new ArrayList<>();
    private List<String> audioFormats = new ArrayList<>();
    private List<String> videoQualities = new ArrayList<>();
    private List<String> audioQualities = new ArrayList<>();
    private File downloadDir;

    private static final int TAB_DOWNLOAD = 0;
    private static final int TAB_HISTORY = 1;
    private static final int TAB_SETTINGS = 2;
    private int currentTab = TAB_DOWNLOAD;

    private ScrollView downloaderView;
    private ScrollView historyView;
    private ScrollView settingsView;

    private LinearLayout tabDownloaderButton;
    private LinearLayout tabHistoryButton;
    private LinearLayout tabSettingsButton;

    private LinearLayout historyListContainer;
    private String currentLanguage;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        loadLanguage();
        loadThemeColors();

        getWindow().setStatusBarColor(Color.TRANSPARENT);
        getWindow().setNavigationBarColor(Color.TRANSPARENT);
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
            getWindow().setDecorFitsSystemWindows(false);
        } else {
            getWindow().getDecorView().setSystemUiVisibility(
                    View.SYSTEM_UI_FLAG_LAYOUT_STABLE
                            | View.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN
                            | View.SYSTEM_UI_FLAG_LAYOUT_HIDE_NAVIGATION);
        }

        backend = Python.getInstance().getModule("mediaflow_core");

        SharedPreferences prefs = getSharedPreferences("mediaflow_prefs", MODE_PRIVATE);
        String savedPath = prefs.getString("download_path", "");
        if (!savedPath.isEmpty()) {
            downloadDir = new File(savedPath);
        } else {
            downloadDir = Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_DOWNLOADS);
            if (downloadDir == null) {
                downloadDir = getExternalFilesDir(Environment.DIRECTORY_DOWNLOADS);
            }
        }
        if (downloadDir != null) {
            downloadDir.mkdirs();
        }

        requestNotificationPermission();
        checkStoragePermission();
        loadBackendOptions();
        buildUi();
        updateModeChoices();
        switchTab(TAB_DOWNLOAD);
    }

    @Override
    protected void onDestroy() {
        executor.shutdownNow();
        super.onDestroy();
    }

    private void loadThemeColors() {
        SharedPreferences prefs = getSharedPreferences("mediaflow_prefs", MODE_PRIVATE);
        String theme = prefs.getString("theme", "dark");
        if ("light".equals(theme)) {
            BG = Color.rgb(244, 246, 249);
            PANEL = Color.rgb(255, 255, 255);
            CARD = Color.rgb(255, 255, 255);
            INPUT = Color.rgb(238, 240, 245);
            TEXT = Color.rgb(30, 41, 59);
            MUTED = Color.rgb(100, 116, 139);
        } else if ("oled".equals(theme)) {
            BG = Color.rgb(0, 0, 0);
            PANEL = Color.rgb(18, 18, 18);
            CARD = Color.rgb(24, 24, 24);
            INPUT = Color.rgb(10, 10, 10);
            TEXT = Color.rgb(255, 255, 255);
            MUTED = Color.rgb(136, 136, 136);
        } else {
            BG = Color.rgb(21, 24, 32);
            PANEL = Color.rgb(33, 37, 46);
            CARD = Color.rgb(40, 45, 56);
            INPUT = Color.rgb(28, 32, 40);
            TEXT = Color.rgb(232, 236, 244);
            MUTED = Color.rgb(154, 164, 184);
        }
    }

    private void loadLanguage() {
        SharedPreferences prefs = getSharedPreferences("mediaflow_prefs", MODE_PRIVATE);
        currentLanguage = prefs.getString("lang", "en");
    }

    private String tr(String key) {
        boolean isArabic = "ar".equals(currentLanguage);
        if (isArabic) {
            switch (key) {
                case "Universal Downloader": return "منزل الميديا العالمي";
                case "Download": return "تحميل";
                case "History": return "السجل";
                case "Settings": return "الإعدادات";
                case "MEDIA / PLAYLIST URL": return "رابط الميديا / قائمة التشغيل";
                case "Paste a YouTube or supported media link": return "الصق رابط يوتيوب أو فيديو مدعوم";
                case "Paste": return "لصق";
                case "Analyse": return "تحليل";
                case "Play Preview": return "معاينة التشغيل";
                case "Paste a link and click Analyse to load media info": return "أدخل الرابط ثم اضغط تحليل لعرض معلومات الميديا";
                case "MEDIA INFO": return "معلومات الميديا";
                case "OPTIONS": return "الخيارات";
                case "MEDIA TYPE": return "نوع الميديا";
                case "Video": return "فيديو";
                case "Audio": return "صوت";
                case "FORMAT": return "الصيغة";
                case "QUALITY": return "الجودة";
                case "Full Playlist": return "قائمة كاملة";
                case "Subtitles": return "الترجمة المصاحبة";
                case "Embed Thumbnail": return "تضمين الصورة المصغرة";
                case "SponsorBlock": return "تخطي إعلانات الرعاة";
                case "PROGRESS": return "التقدم";
                case "Idle - ready to download": return "جاهز للتحميل";
                case "Start Download": return "بدء التحميل";
                case "Cancel": return "إلغاء";
                case "CONSOLE OUTPUT": return "مخرجات النظام";
                case "Clear": return "مسح";
                case "Theme": return "المظهر";
                case "Language": return "اللغة";
                case "Download Location": return "موقع التحميل";
                case "Save": return "حفظ";
                case "Dark": return "داكن";
                case "Light": return "فاتح";
                case "OLED": return "أوليد (أسود مطفأ)";
                case "No media analysed yet": return "لم يتم تحليل ميديا بعد";
                case "No downloaded files found": return "لم يتم العثور على ملفات محملة";
                case "Play": return "تشغيل";
                case "Share": return "مشاركة";
                case "Delete": return "حذف";
                case "Saved!": return "تم الحفظ!";
                case "Invalid directory path": return "مسار المجلد غير صالح";
                case "Error: ": return "خطأ: ";
                case "Cannot play file: ": return "لا يمكن تشغيل الملف: ";
                case "Cannot share file: ": return "لا يمكن مشاركة الملف: ";
                case "Share via": return "مشاركة عبر";
                case "Deleted successfully": return "تم الحذف بنجاح";
                case "Failed to delete file": return "فشل حذف الملف";
                case "Supported by yt-dlp: YouTube, Facebook, Instagram, TikTok, X/Twitter, and many more":
                    return "المنصات المدعومة: يوتيوب، فيسبوك، انستغرام، تيك توك، إكس، والمزيد";
            }
        }
        return key;
    }

    private int textGravity() {
        return "ar".equals(currentLanguage) ? Gravity.RIGHT : Gravity.LEFT;
    }

    private void requestNotificationPermission() {
        if (Build.VERSION.SDK_INT >= 33
                && checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED) {
            requestPermissions(new String[]{Manifest.permission.POST_NOTIFICATIONS}, 20);
        }
    }

    private void checkStoragePermission() {
        if (Build.VERSION.SDK_INT >= 30) {
            if (!Environment.isExternalStorageManager()) {
                try {
                    Intent intent = new Intent(Settings.ACTION_MANAGE_APP_ALL_FILES_ACCESS_PERMISSION);
                    intent.addCategory("android.intent.category.DEFAULT");
                    intent.setData(Uri.parse(String.format("package:%s", getApplicationContext().getPackageName())));
                    startActivityForResult(intent, 2296);
                } catch (Exception e) {
                    Intent intent = new Intent();
                    intent.setAction(Settings.ACTION_MANAGE_ALL_FILES_ACCESS_PERMISSION);
                    startActivityForResult(intent, 2296);
                }
            }
        } else {
            if (checkSelfPermission(Manifest.permission.WRITE_EXTERNAL_STORAGE) != PackageManager.PERMISSION_GRANTED) {
                requestPermissions(new String[]{
                        Manifest.permission.WRITE_EXTERNAL_STORAGE,
                        Manifest.permission.READ_EXTERNAL_STORAGE
                }, 101);
            }
        }
    }

    private void loadBackendOptions() {
        try {
            JSONObject options = new JSONObject(backend.callAttr("get_options").toString());
            videoFormats = jsonList(options.getJSONArray("video_formats"));
            audioFormats = jsonList(options.getJSONArray("audio_formats"));
            videoQualities = jsonList(options.getJSONArray("video_qualities"));
            audioQualities = jsonList(options.getJSONArray("audio_qualities"));
        } catch (Exception exc) {
            videoFormats = listOf("mp4", "webm", "mkv");
            audioFormats = listOf("mp3", "m4a", "opus");
            videoQualities = listOf("Best Available", "720p (HD)", "480p", "Worst");
            audioQualities = listOf("Best", "192 kbps", "128 kbps", "Worst");
        }
    }

    private void buildUi() {
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setBackgroundColor(BG);
        root.setOnApplyWindowInsetsListener((v, insets) -> {
            v.setPadding(0, insets.getSystemWindowInsetTop(), 0, insets.getSystemWindowInsetBottom());
            return insets;
        });

        // Header
        LinearLayout header = new LinearLayout(this);
        header.setOrientation(LinearLayout.HORIZONTAL);
        header.setGravity(Gravity.CENTER_VERTICAL);
        header.setPadding(dp(18), dp(14), dp(18), dp(14));
        header.setBackgroundColor(PANEL);

        TextView logo = new TextView(this);
        logo.setText("▶");
        logo.setTextSize(24);
        logo.setTextColor(ACCENT);
        logo.setPadding("ar".equals(currentLanguage) ? dp(12) : 0, 0, "ar".equals(currentLanguage) ? 0 : dp(12), 0);

        LinearLayout headerTextContainer = new LinearLayout(this);
        headerTextContainer.setOrientation(LinearLayout.VERTICAL);

        TextView appNameLabel = new TextView(this);
        appNameLabel.setText("MediaFlow");
        appNameLabel.setTextSize(20);
        appNameLabel.setTextColor(TEXT);
        appNameLabel.setTypeface(Typeface.DEFAULT, Typeface.BOLD);

        TextView appSubLabel = new TextView(this);
        appSubLabel.setText(tr("Universal Downloader"));
        appSubLabel.setTextSize(11);
        appSubLabel.setTextColor(MUTED);

        headerTextContainer.addView(appNameLabel);
        headerTextContainer.addView(appSubLabel);

        header.addView(logo);
        header.addView(headerTextContainer);
        root.addView(header);

        View divider = new View(this);
        divider.setBackgroundColor(Color.rgb(46, 52, 65));
        divider.setLayoutParams(new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(1)));
        root.addView(divider);

        FrameLayout contentFrame = new FrameLayout(this);
        LinearLayout.LayoutParams contentParams = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                0,
                1
        );
        contentFrame.setLayoutParams(contentParams);
        root.addView(contentFrame);

        downloaderView = buildDownloaderView();
        historyView = buildHistoryView();
        settingsView = buildSettingsView();

        contentFrame.addView(downloaderView);
        contentFrame.addView(historyView);
        contentFrame.addView(settingsView);

        View botDivider = new View(this);
        botDivider.setBackgroundColor(Color.rgb(46, 52, 65));
        botDivider.setLayoutParams(new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(1)));
        root.addView(botDivider);

        LinearLayout bottomBar = buildBottomNavBar();
        root.addView(bottomBar);

        setContentView(root);
    }

    private ScrollView buildDownloaderView() {
        ScrollView scroll = new ScrollView(this);
        scroll.setFillViewport(true);
        scroll.setBackgroundColor(BG);

        LinearLayout layout = new LinearLayout(this);
        layout.setOrientation(LinearLayout.VERTICAL);
        layout.setPadding(dp(16), dp(16), dp(16), dp(16));
        scroll.addView(layout);

        // 1. URL Card
        LinearLayout urlCard = card();
        urlCard.addView(sectionLabel("MEDIA / PLAYLIST URL"));

        LinearLayout urlRow = new LinearLayout(this);
        urlRow.setOrientation(LinearLayout.HORIZONTAL);
        urlRow.setGravity(Gravity.CENTER_VERTICAL);

        urlEdit = new EditText(this);
        urlEdit.setHint(tr("Paste a YouTube or supported media link"));
        urlEdit.setSingleLine(true);
        urlEdit.setTextColor(TEXT);
        urlEdit.setHintTextColor(MUTED);
        urlEdit.setTextSize(15);
        urlEdit.setPadding(dp(12), 0, dp(12), 0);
        urlEdit.setGravity(textGravity());

        GradientDrawable editBg = new GradientDrawable();
        editBg.setColor(INPUT);
        editBg.setCornerRadius(dp(6));
        editBg.setStroke(dp(1), Color.rgb(46, 52, 65));
        urlEdit.setBackground(editBg);

        LinearLayout.LayoutParams editParams = new LinearLayout.LayoutParams(0, dp(48), 1);
        editParams.setMargins(0, 0, dp(8), 0);
        urlEdit.setLayoutParams(editParams);

        Button pasteButton = button("Paste", PANEL);
        pasteButton.setTextColor(TEXT);
        GradientDrawable pasteBg = new GradientDrawable();
        pasteBg.setColor(PANEL);
        pasteBg.setCornerRadius(dp(6));
        pasteBg.setStroke(dp(1), Color.rgb(70, 78, 96));
        pasteButton.setBackground(pasteBg);
        pasteButton.setPadding(dp(12), 0, dp(12), 0);
        LinearLayout.LayoutParams pasteParams = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.WRAP_CONTENT, dp(48));
        pasteParams.setMargins(0, 0, dp(8), 0);
        pasteButton.setLayoutParams(pasteParams);

        Button analyseButton = button("Analyse", ACCENT);
        analyseButton.setTextColor(Color.WHITE);
        LinearLayout.LayoutParams analyseParams = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.WRAP_CONTENT, dp(48));
        analyseButton.setLayoutParams(analyseParams);

        urlRow.addView(urlEdit);
        urlRow.addView(pasteButton);
        urlRow.addView(analyseButton);
        urlCard.addView(urlRow);

        TextView urlHelp = label("Supported by yt-dlp: YouTube, Facebook, Instagram, TikTok, X/Twitter, and many more", 11, MUTED, Typeface.NORMAL);
        urlHelp.setPadding(0, dp(6), 0, 0);
        urlCard.addView(urlHelp);
        layout.addView(urlCard);

        pasteButton.setOnClickListener(v -> {
            android.content.ClipboardManager clipboard = (android.content.ClipboardManager) getSystemService(Context.CLIPBOARD_SERVICE);
            if (clipboard != null && clipboard.hasPrimaryClip()) {
                android.content.ClipData clip = clipboard.getPrimaryClip();
                if (clip != null && clip.getItemCount() > 0) {
                    CharSequence text = clip.getItemAt(0).getText();
                    if (text != null) {
                        urlEdit.setText(text.toString());
                    }
                }
            }
        });

        // 2. Media Info Card
        LinearLayout infoCard = card();
        infoCard.addView(sectionLabel("MEDIA INFO"));

        LinearLayout infoRow = new LinearLayout(this);
        infoRow.setOrientation(LinearLayout.HORIZONTAL);
        infoRow.setGravity(Gravity.CENTER_VERTICAL);

        FrameLayout thumbBox = new FrameLayout(this);
        GradientDrawable thumbBg = new GradientDrawable();
        thumbBg.setColor(INPUT);
        thumbBg.setCornerRadius(dp(4));
        thumbBox.setBackground(thumbBg);
        LinearLayout.LayoutParams thumbParams = new LinearLayout.LayoutParams(dp(80), dp(60));
        thumbParams.setMargins("ar".equals(currentLanguage) ? dp(12) : 0, 0, "ar".equals(currentLanguage) ? 0 : dp(12), 0);
        thumbBox.setLayoutParams(thumbParams);

        TextView thumbText = new TextView(this);
        thumbText.setText(tr("Play Preview"));
        thumbText.setTextSize(10);
        thumbText.setTextColor(MUTED);
        thumbText.setGravity(Gravity.CENTER);
        FrameLayout.LayoutParams textParams = new FrameLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT);
        thumbText.setLayoutParams(textParams);

        thumbImage = new ImageView(this);
        thumbImage.setScaleType(ImageView.ScaleType.CENTER_CROP);
        FrameLayout.LayoutParams imgParams = new FrameLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT);
        thumbImage.setScaleType(ImageView.ScaleType.CENTER_CROP);
        thumbImage.setLayoutParams(imgParams);
        thumbImage.setVisibility(View.GONE);

        thumbBox.addView(thumbText);
        thumbBox.addView(thumbImage);

        LinearLayout infoTextCol = new LinearLayout(this);
        infoTextCol.setOrientation(LinearLayout.VERTICAL);
        LinearLayout.LayoutParams infoTextColParams = new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1);
        infoTextCol.setLayoutParams(infoTextColParams);

        infoTitle = label("No media analysed yet", 14, TEXT, Typeface.BOLD);
        infoMeta = label("", 12, MUTED, Typeface.NORMAL);
        infoTextCol.addView(infoTitle);
        infoTextCol.addView(infoMeta);

        infoRow.addView(thumbBox);
        infoRow.addView(infoTextCol);
        infoCard.addView(infoRow);
        layout.addView(infoCard);

        // 3. Options Card
        LinearLayout optionsCard = card();
        optionsCard.addView(sectionLabel("OPTIONS"));

        TextView typeLabel = smallLabel("MEDIA TYPE");
        optionsCard.addView(typeLabel);

        RadioGroup modeGroup = new RadioGroup(this);
        modeGroup.setOrientation(RadioGroup.HORIZONTAL);
        videoRadio = radio("Video");
        audioRadio = radio("Audio");
        videoRadio.setChecked(true);
        modeGroup.addView(videoRadio);
        modeGroup.addView(space(dp(20), 1));
        modeGroup.addView(audioRadio);
        optionsCard.addView(modeGroup);

        LinearLayout spinnersRow = new LinearLayout(this);
        spinnersRow.setOrientation(LinearLayout.HORIZONTAL);
        spinnersRow.setPadding(0, dp(8), 0, dp(8));

        LinearLayout formatCol = new LinearLayout(this);
        formatCol.setOrientation(LinearLayout.VERTICAL);
        LinearLayout.LayoutParams colParams1 = new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1);
        colParams1.setMargins(0, 0, dp(8), 0);
        formatCol.setLayoutParams(colParams1);
        formatCol.addView(smallLabel("FORMAT"));
        formatSpinner = spinner();
        formatCol.addView(formatSpinner);

        LinearLayout qualityCol = new LinearLayout(this);
        qualityCol.setOrientation(LinearLayout.VERTICAL);
        LinearLayout.LayoutParams colParams2 = new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1);
        qualityCol.setLayoutParams(colParams2);
        qualityCol.addView(smallLabel("QUALITY"));
        qualitySpinner = spinner();
        qualityCol.addView(qualitySpinner);

        spinnersRow.addView(formatCol);
        spinnersRow.addView(qualityCol);
        optionsCard.addView(spinnersRow);

        LinearLayout cbContainer = new LinearLayout(this);
        cbContainer.setOrientation(LinearLayout.VERTICAL);
        cbContainer.setPadding(0, dp(8), 0, 0);

        LinearLayout cbRow1 = new LinearLayout(this);
        cbRow1.setOrientation(LinearLayout.HORIZONTAL);

        playlistCheck = check("Full Playlist");
        subsCheck = check("Subtitles");
        LinearLayout.LayoutParams cbParams1 = new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1);
        playlistCheck.setLayoutParams(cbParams1);
        subsCheck.setLayoutParams(cbParams1);
        cbRow1.addView(playlistCheck);
        cbRow1.addView(subsCheck);

        LinearLayout cbRow2 = new LinearLayout(this);
        cbRow2.setOrientation(LinearLayout.HORIZONTAL);

        thumbCheck = check("Embed Thumbnail");
        sponsorCheck = check("SponsorBlock");
        LinearLayout.LayoutParams cbParams2 = new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1);
        thumbCheck.setLayoutParams(cbParams2);
        sponsorCheck.setLayoutParams(cbParams2);
        cbRow2.addView(thumbCheck);
        cbRow2.addView(sponsorCheck);

        cbContainer.addView(cbRow1);
        cbContainer.addView(cbRow2);
        optionsCard.addView(cbContainer);
        layout.addView(optionsCard);

        // 4. Progress Card
        LinearLayout progressCard = card();
        progressCard.addView(sectionLabel("PROGRESS"));

        progressBar = new ProgressBar(this, null, android.R.attr.progressBarStyleHorizontal);
        progressBar.setMax(1000);
        progressCard.addView(progressBar, matchWrap());

        statusText = label("Idle - ready to download", 14, TEXT, Typeface.BOLD);
        speedText = label("", 12, MUTED, Typeface.NORMAL);
        progressCard.addView(statusText);
        progressCard.addView(speedText);

        LinearLayout actionButtonsRow = new LinearLayout(this);
        actionButtonsRow.setOrientation(LinearLayout.HORIZONTAL);
        actionButtonsRow.setPadding(0, dp(10), 0, 0);

        downloadButton = button("Start Download", ACCENT);
        downloadButton.setTextColor(Color.WHITE);
        LinearLayout.LayoutParams dlBtnParams = new LinearLayout.LayoutParams(0, dp(48), 2);
        dlBtnParams.setMargins(0, 0, dp(8), 0);
        downloadButton.setLayoutParams(dlBtnParams);

        cancelButton = button("Cancel", DANGER);
        cancelButton.setEnabled(false);
        GradientDrawable cancelBg = new GradientDrawable();
        cancelBg.setColor(Color.TRANSPARENT);
        cancelBg.setCornerRadius(dp(6));
        cancelBg.setStroke(dp(1), DANGER);
        cancelButton.setBackground(cancelBg);
        cancelButton.setTextColor(DANGER);
        LinearLayout.LayoutParams cncBtnParams = new LinearLayout.LayoutParams(0, dp(48), 1);
        cancelButton.setLayoutParams(cncBtnParams);

        actionButtonsRow.addView(downloadButton);
        actionButtonsRow.addView(cancelButton);
        progressCard.addView(actionButtonsRow);
        layout.addView(progressCard);

        // 5. Console Output Card
        LinearLayout logCard = card();

        LinearLayout logHeader = new LinearLayout(this);
        logHeader.setOrientation(LinearLayout.HORIZONTAL);
        logHeader.setGravity(Gravity.CENTER_VERTICAL);

        TextView logTitle = sectionLabel("CONSOLE OUTPUT");
        LinearLayout.LayoutParams logTitleParams = new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1);
        logTitle.setLayoutParams(logTitleParams);

        TextView logClear = new TextView(this);
        logClear.setText(tr("Clear"));
        logClear.setTextSize(12);
        logClear.setTextColor(ACCENT);
        logClear.setTypeface(Typeface.DEFAULT, Typeface.BOLD);
        logClear.setClickable(true);
        logClear.setFocusable(true);
        logClear.setOnClickListener(v -> logText.setText(""));

        logHeader.addView(logTitle);
        logHeader.addView(logClear);
        logCard.addView(logHeader);

        ScrollView logScroll = new ScrollView(this);
        LinearLayout.LayoutParams logScrollParams = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(120));
        logScroll.setLayoutParams(logScrollParams);

        logText = new TextView(this);
        logText.setTextSize(11);
        logText.setTextColor(MUTED);
        logText.setTypeface(Typeface.MONOSPACE);
        logText.setLineSpacing(0, 1.1f);
        logScroll.addView(logText);

        logCard.addView(logScroll);
        layout.addView(logCard);

        analyseButton.setOnClickListener(v -> analyse());
        downloadButton.setOnClickListener(v -> download());
        cancelButton.setOnClickListener(v -> cancelDownload());
        modeGroup.setOnCheckedChangeListener((group, checkedId) -> updateModeChoices());

        return scroll;
    }

    private ScrollView buildSettingsView() {
        ScrollView scroll = new ScrollView(this);
        scroll.setFillViewport(true);
        scroll.setBackgroundColor(BG);

        LinearLayout layout = new LinearLayout(this);
        layout.setOrientation(LinearLayout.VERTICAL);
        layout.setPadding(dp(16), dp(16), dp(16), dp(16));
        scroll.addView(layout);

        TextView title = label("Settings", 20, TEXT, Typeface.BOLD);
        title.setPadding(0, 0, 0, dp(16));
        layout.addView(title);

        SharedPreferences prefs = getSharedPreferences("mediaflow_prefs", MODE_PRIVATE);

        // Theme Card
        LinearLayout themeCard = card();
        themeCard.addView(sectionLabel("Theme"));

        RadioGroup themeGroup = new RadioGroup(this);
        themeGroup.setOrientation(RadioGroup.VERTICAL);

        RadioButton darkBtn = radio("Dark");
        RadioButton lightBtn = radio("Light");
        RadioButton oledBtn = radio("OLED");

        themeGroup.addView(darkBtn);
        themeGroup.addView(lightBtn);
        themeGroup.addView(oledBtn);

        String savedTheme = prefs.getString("theme", "dark");
        if ("light".equals(savedTheme)) lightBtn.setChecked(true);
        else if ("oled".equals(savedTheme)) oledBtn.setChecked(true);
        else darkBtn.setChecked(true);

        themeGroup.setOnCheckedChangeListener((group, checkedId) -> {
            String selectedTheme = "dark";
            if (checkedId == lightBtn.getId()) selectedTheme = "light";
            else if (checkedId == oledBtn.getId()) selectedTheme = "oled";

            prefs.edit().putString("theme", selectedTheme).apply();
            recreate();
        });

        themeCard.addView(themeGroup);
        layout.addView(themeCard);

        // Language Card
        LinearLayout langCard = card();
        langCard.addView(sectionLabel("Language"));

        RadioGroup langGroup = new RadioGroup(this);
        langGroup.setOrientation(RadioGroup.VERTICAL);

        RadioButton enBtn = radio("English");
        RadioButton arBtn = radio("العربية (Arabic)");

        langGroup.addView(enBtn);
        langGroup.addView(arBtn);

        String savedLang = prefs.getString("lang", "en");
        if ("ar".equals(savedLang)) arBtn.setChecked(true);
        else enBtn.setChecked(true);

        langGroup.setOnCheckedChangeListener((group, checkedId) -> {
            String selectedLang = "en";
            if (checkedId == arBtn.getId()) selectedLang = "ar";

            prefs.edit().putString("lang", selectedLang).apply();
            recreate();
        });

        langCard.addView(langGroup);
        layout.addView(langCard);

        // Download Path Card
        LinearLayout folderCard = card();
        folderCard.addView(sectionLabel("Download Location"));

        EditText pathEdit = new EditText(this);
        pathEdit.setText(downloadDir.getAbsolutePath());
        pathEdit.setTextColor(TEXT);
        pathEdit.setTextSize(14);
        pathEdit.setPadding(dp(12), 0, dp(12), 0);
        pathEdit.setSingleLine(true);

        GradientDrawable pathBg = new GradientDrawable();
        pathBg.setColor(INPUT);
        pathBg.setCornerRadius(dp(6));
        pathBg.setStroke(dp(1), Color.rgb(46, 52, 65));
        pathEdit.setBackground(pathBg);

        LinearLayout.LayoutParams pathParams = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(48));
        pathParams.setMargins(0, dp(6), 0, dp(10));
        pathEdit.setLayoutParams(pathParams);
        folderCard.addView(pathEdit);

        Button saveBtn = button("Save", ACCENT);
        saveBtn.setTextColor(Color.WHITE);
        LinearLayout.LayoutParams saveParams = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.WRAP_CONTENT, dp(40));
        saveBtn.setLayoutParams(saveParams);

        saveBtn.setOnClickListener(v -> {
            String newPath = pathEdit.getText().toString().trim();
            if (newPath.isEmpty()) {
                Toast.makeText(this, tr("Invalid directory path"), Toast.LENGTH_SHORT).show();
                return;
            }
            File f = new File(newPath);
            try {
                if (f.exists() || f.mkdirs()) {
                    downloadDir = f;
                    prefs.edit().putString("download_path", newPath).apply();
                    Toast.makeText(this, tr("Saved!"), Toast.LENGTH_SHORT).show();
                    refreshHistoryList();
                } else {
                    Toast.makeText(this, tr("Invalid directory path"), Toast.LENGTH_SHORT).show();
                }
            } catch (Exception e) {
                Toast.makeText(this, tr("Error: ") + e.getMessage(), Toast.LENGTH_SHORT).show();
            }
        });

        folderCard.addView(saveBtn);
        layout.addView(folderCard);

        // FFmpeg Configuration Card
        LinearLayout ffmpegCard = card();
        ffmpegCard.addView(sectionLabel("FFmpeg (Optional)"));

        CheckBox ffmpegCb = check("Enable FFmpeg processing");
        ffmpegCb.setChecked(prefs.getBoolean("allow_ffmpeg", false));
        ffmpegCard.addView(ffmpegCb);

        ffmpegCard.addView(smallLabel("FFmpeg folder or binary path"));
        EditText ffmpegPathEdit = new EditText(this);
        ffmpegPathEdit.setText(prefs.getString("ffmpeg_path", ""));
        ffmpegPathEdit.setTextColor(TEXT);
        ffmpegPathEdit.setTextSize(14);
        ffmpegPathEdit.setPadding(dp(12), 0, dp(12), 0);
        ffmpegPathEdit.setSingleLine(true);

        GradientDrawable ffBg = new GradientDrawable();
        ffBg.setColor(INPUT);
        ffBg.setCornerRadius(dp(6));
        ffBg.setStroke(dp(1), Color.rgb(46, 52, 65));
        ffmpegPathEdit.setBackground(ffBg);

        LinearLayout.LayoutParams ffParams = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(48));
        ffParams.setMargins(0, dp(6), 0, dp(10));
        ffmpegPathEdit.setLayoutParams(ffParams);
        ffmpegCard.addView(ffmpegPathEdit);

        Button saveFfBtn = button("Save", ACCENT);
        saveFfBtn.setTextColor(Color.WHITE);
        LinearLayout.LayoutParams saveFfParams = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.WRAP_CONTENT, dp(40));
        saveFfBtn.setLayoutParams(saveFfParams);

        saveFfBtn.setOnClickListener(v -> {
            boolean enabled = ffmpegCb.isChecked();
            String path = ffmpegPathEdit.getText().toString().trim();
            prefs.edit()
                .putBoolean("allow_ffmpeg", enabled)
                .putString("ffmpeg_path", path)
                .apply();
            Toast.makeText(this, tr("Saved!"), Toast.LENGTH_SHORT).show();
        });

        ffmpegCard.addView(saveFfBtn);
        layout.addView(ffmpegCard);

        return scroll;
    }

    private ScrollView buildHistoryView() {
        ScrollView scroll = new ScrollView(this);
        scroll.setFillViewport(true);
        scroll.setBackgroundColor(BG);

        LinearLayout layout = new LinearLayout(this);
        layout.setOrientation(LinearLayout.VERTICAL);
        layout.setPadding(dp(16), dp(16), dp(16), dp(16));
        scroll.addView(layout);

        TextView title = label("History", 20, TEXT, Typeface.BOLD);
        title.setPadding(0, 0, 0, dp(16));
        layout.addView(title);

        historyListContainer = new LinearLayout(this);
        historyListContainer.setOrientation(LinearLayout.VERTICAL);
        layout.addView(historyListContainer);

        return scroll;
    }

    private void refreshHistoryList() {
        if (historyListContainer == null) return;
        historyListContainer.removeAllViews();

        File[] files = downloadDir.listFiles();
        List<File> mediaFiles = new ArrayList<>();
        if (files != null) {
            for (File f : files) {
                if (f.isFile()) {
                    String name = f.getName().toLowerCase();
                    if (name.endsWith(".mp4") || name.endsWith(".mkv") || name.endsWith(".webm") ||
                            name.endsWith(".mp3") || name.endsWith(".m4a") || name.endsWith(".aac") ||
                            name.endsWith(".opus") || name.endsWith(".wav") || name.endsWith(".ogg") ||
                            name.endsWith(".flac")) {
                        mediaFiles.add(f);
                    }
                }
            }
        }

        if (mediaFiles.isEmpty()) {
            TextView emptyText = label("No downloaded files found", 14, MUTED, Typeface.NORMAL);
            emptyText.setGravity(Gravity.CENTER);
            emptyText.setPadding(0, dp(40), 0, 0);
            historyListContainer.addView(emptyText);
            return;
        }

        mediaFiles.sort((f1, f2) -> Long.compare(f2.lastModified(), f1.lastModified()));

        for (File f : mediaFiles) {
            LinearLayout fileCard = card();

            LinearLayout detailsRow = new LinearLayout(this);
            detailsRow.setOrientation(LinearLayout.HORIZONTAL);
            detailsRow.setGravity(Gravity.CENTER_VERTICAL);

            TextView typeIcon = new TextView(this);
            String name = f.getName().toLowerCase();
            boolean isVideo = name.endsWith(".mp4") || name.endsWith(".mkv") || name.endsWith(".webm");
            typeIcon.setText(isVideo ? "🎥" : "🎵");
            typeIcon.setTextSize(20);
            typeIcon.setPadding("ar".equals(currentLanguage) ? dp(10) : 0, 0, "ar".equals(currentLanguage) ? 0 : dp(10), 0);

            LinearLayout textCol = new LinearLayout(this);
            textCol.setOrientation(LinearLayout.VERTICAL);
            LinearLayout.LayoutParams textColParams = new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1);
            textCol.setLayoutParams(textColParams);

            TextView nameText = new TextView(this);
            nameText.setText(f.getName());
            nameText.setTextColor(TEXT);
            nameText.setTextSize(14);
            nameText.setTypeface(Typeface.DEFAULT, Typeface.BOLD);
            nameText.setGravity(textGravity());

            TextView sizeText = new TextView(this);
            sizeText.setText(fmtSize(f.length()));
            sizeText.setTextColor(MUTED);
            sizeText.setTextSize(12);
            sizeText.setGravity(textGravity());

            textCol.addView(nameText);
            textCol.addView(sizeText);

            detailsRow.addView(typeIcon);
            detailsRow.addView(textCol);
            fileCard.addView(detailsRow);

            LinearLayout buttonsRow = new LinearLayout(this);
            buttonsRow.setOrientation(LinearLayout.HORIZONTAL);
            buttonsRow.setPadding(0, dp(12), 0, 0);
            buttonsRow.setGravity("ar".equals(currentLanguage) ? Gravity.LEFT : Gravity.RIGHT);

            Button playBtn = button("Play", ACCENT);
            playBtn.setTextColor(Color.WHITE);
            LinearLayout.LayoutParams playParams = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.WRAP_CONTENT, dp(36));
            playParams.setMargins(0, 0, dp(8), 0);
            playBtn.setLayoutParams(playParams);

            Button shareBtn = button("Share", PANEL);
            shareBtn.setTextColor(TEXT);
            GradientDrawable shareBg = new GradientDrawable();
            shareBg.setColor(PANEL);
            shareBg.setCornerRadius(dp(6));
            shareBg.setStroke(dp(1), Color.rgb(70, 78, 96));
            shareBtn.setBackground(shareBg);
            LinearLayout.LayoutParams shareParams = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.WRAP_CONTENT, dp(36));
            shareParams.setMargins(0, 0, dp(8), 0);
            shareBtn.setLayoutParams(shareParams);

            Button deleteBtn = button("Delete", DANGER);
            deleteBtn.setTextColor(DANGER);
            GradientDrawable deleteBg = new GradientDrawable();
            deleteBg.setColor(Color.TRANSPARENT);
            deleteBg.setCornerRadius(dp(6));
            deleteBg.setStroke(dp(1), DANGER);
            deleteBtn.setBackground(deleteBg);
            LinearLayout.LayoutParams deleteParams = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.WRAP_CONTENT, dp(36));
            deleteBtn.setLayoutParams(deleteParams);

            buttonsRow.addView(playBtn);
            buttonsRow.addView(shareBtn);
            buttonsRow.addView(deleteBtn);
            fileCard.addView(buttonsRow);

            playBtn.setOnClickListener(v -> playFile(f));
            shareBtn.setOnClickListener(v -> shareFile(f));
            deleteBtn.setOnClickListener(v -> deleteFile(f));

            historyListContainer.addView(fileCard);
        }
    }

    private String fmtSize(long bytes) {
        if (bytes < 1024) return bytes + " B";
        int exp = (int) (Math.log(bytes) / Math.log(1024));
        char pre = "KMGTPE".charAt(exp-1);
        return String.format("%.1f %cB", bytes / Math.pow(1024, exp), pre);
    }

    private void playFile(File file) {
        try {
            Uri uri = FileProvider.getUriForFile(this, getPackageName() + ".fileprovider", file);
            Intent intent = new Intent(Intent.ACTION_VIEW);
            intent.setDataAndType(uri, getMimeType(file));
            intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);
            startActivity(intent);
        } catch (Exception e) {
            Toast.makeText(this, tr("Cannot play file: ") + e.getMessage(), Toast.LENGTH_LONG).show();
        }
    }

    private void shareFile(File file) {
        try {
            Uri uri = FileProvider.getUriForFile(this, getPackageName() + ".fileprovider", file);
            Intent intent = new Intent(Intent.ACTION_SEND);
            intent.setType(getMimeType(file));
            intent.putExtra(Intent.EXTRA_STREAM, uri);
            intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);
            startActivity(Intent.createChooser(intent, tr("Share via")));
        } catch (Exception e) {
            Toast.makeText(this, tr("Cannot share file: ") + e.getMessage(), Toast.LENGTH_LONG).show();
        }
    }

    private void deleteFile(File file) {
        try {
            if (file.delete()) {
                Toast.makeText(this, tr("Deleted successfully"), Toast.LENGTH_SHORT).show();
                MediaScannerConnection.scanFile(
                        this,
                        new String[]{file.getAbsolutePath()},
                        null,
                        null
                );
                refreshHistoryList();
            } else {
                Toast.makeText(this, tr("Failed to delete file"), Toast.LENGTH_SHORT).show();
            }
        } catch (Exception e) {
            Toast.makeText(this, tr("Error: ") + e.getMessage(), Toast.LENGTH_SHORT).show();
        }
    }

    private String getMimeType(File file) {
        String name = file.getName().toLowerCase();
        if (name.endsWith(".mp3")) return "audio/mp3";
        if (name.endsWith(".m4a")) return "audio/m4a";
        if (name.endsWith(".aac")) return "audio/aac";
        if (name.endsWith(".opus")) return "audio/opus";
        if (name.endsWith(".wav")) return "audio/wav";
        if (name.endsWith(".ogg")) return "audio/ogg";
        if (name.endsWith(".flac")) return "audio/flac";
        if (name.endsWith(".mp4")) return "video/mp4";
        if (name.endsWith(".mkv")) return "video/x-matroska";
        if (name.endsWith(".webm")) return "video/webm";
        return "*/*";
    }

    private LinearLayout buildBottomNavBar() {
        LinearLayout bar = new LinearLayout(this);
        bar.setOrientation(LinearLayout.HORIZONTAL);
        bar.setBackgroundColor(PANEL);
        bar.setPadding(0, dp(8), 0, dp(8));

        LinearLayout.LayoutParams params = new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                dp(60)
        );
        bar.setLayoutParams(params);

        tabDownloaderButton = createTabButton("Download", TAB_DOWNLOAD);
        tabHistoryButton = createTabButton("History", TAB_HISTORY);
        tabSettingsButton = createTabButton("Settings", TAB_SETTINGS);

        bar.addView(tabDownloaderButton);
        bar.addView(tabHistoryButton);
        bar.addView(tabSettingsButton);

        return bar;
    }

    private LinearLayout createTabButton(String labelText, int tabIndex) {
        LinearLayout btn = new LinearLayout(this);
        btn.setOrientation(LinearLayout.VERTICAL);
        btn.setGravity(Gravity.CENTER);
        btn.setClickable(true);
        btn.setFocusable(true);

        LinearLayout.LayoutParams params = new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.MATCH_PARENT, 1);
        btn.setLayoutParams(params);

        String icon = "";
        if (tabIndex == TAB_DOWNLOAD) icon = "📥";
        else if (tabIndex == TAB_HISTORY) icon = "📜";
        else icon = "⚙️";

        TextView iconView = new TextView(this);
        iconView.setText(icon);
        iconView.setTextSize(18);
        iconView.setGravity(Gravity.CENTER);

        TextView textView = new TextView(this);
        textView.setText(tr(labelText));
        textView.setTextSize(11);
        textView.setTypeface(Typeface.DEFAULT, Typeface.BOLD);
        textView.setGravity(Gravity.CENTER);

        btn.addView(iconView);
        btn.addView(textView);

        btn.setOnClickListener(v -> switchTab(tabIndex));
        return btn;
    }

    private void switchTab(int tabIndex) {
        currentTab = tabIndex;
        downloaderView.setVisibility(tabIndex == TAB_DOWNLOAD ? View.VISIBLE : View.GONE);
        historyView.setVisibility(tabIndex == TAB_HISTORY ? View.VISIBLE : View.GONE);
        settingsView.setVisibility(tabIndex == TAB_SETTINGS ? View.VISIBLE : View.GONE);

        updateTabButtonStyles();

        if (tabIndex == TAB_HISTORY) {
            refreshHistoryList();
        }
    }

    private void updateTabButtonStyles() {
        updateSingleTabStyle(tabDownloaderButton, currentTab == TAB_DOWNLOAD);
        updateSingleTabStyle(tabHistoryButton, currentTab == TAB_HISTORY);
        updateSingleTabStyle(tabSettingsButton, currentTab == TAB_SETTINGS);
    }

    private void updateSingleTabStyle(LinearLayout btn, boolean active) {
        TextView textView = (TextView) btn.getChildAt(1);
        if (active) {
            textView.setTextColor(ACCENT);
        } else {
            textView.setTextColor(MUTED);
        }
    }

    private void analyse() {
        String url = urlEdit.getText().toString().trim();
        if (url.isEmpty()) {
            setStatus("Paste a URL first", true);
            return;
        }

        setBusy(true, false);
        setStatus("Analysing media link...", false);
        appendLog("Fetching info: " + url);

        executor.submit(() -> {
            String raw = backend.callAttr("fetch_info", url, playlistCheck.isChecked()).toString();
            runOnUiThread(() -> handleInfoResult(raw));
        });
    }

    private void handleInfoResult(String raw) {
        setBusy(false, false);
        try {
            JSONObject result = new JSONObject(raw);
            if (!result.optBoolean("ok")) {
                setStatus(result.optString("error", tr("Could not fetch media")), true);
                appendLog("ERROR  " + result.optString("error"));
                return;
            }
            infoTitle.setText(result.optString("title", "Unknown"));
            List<String> meta = new ArrayList<>();
            addIfPresent(meta, result.optString("extractor"));
            addIfPresent(meta, result.optString("uploader"));
            addIfPresent(meta, result.optString("duration"));
            String views = result.optString("views");
            if (!views.isEmpty()) {
                meta.add(views + " views");
            }
            int formats = result.optInt("formats", 0);
            if (formats > 0) {
                meta.add(formats + " formats");
            }
            String thumbnailUrl = result.optString("thumbnail");
            if (!thumbnailUrl.isEmpty()) {
                loadThumbnail(thumbnailUrl);
            } else {
                thumbImage.setVisibility(View.GONE);
            }

            infoMeta.setText(join(meta, "  |  "));
            setStatus("Media info loaded", false);
            appendLog("OK  " + result.optString("title"));
        } catch (Exception exc) {
            setStatus("Could not parse media info", true);
            appendLog("ERROR  " + exc.getMessage());
        }
    }

    private void download() {
        String url = urlEdit.getText().toString().trim();
        if (url.isEmpty()) {
            setStatus("Paste a URL first", true);
            return;
        }
        if (downloadDir == null) {
            setStatus("Android did not provide an app download folder", true);
            return;
        }

        setBusy(true, true);
        progressBar.setProgress(0);
        setStatus("Starting download...", false);
        appendLog("Starting download to " + downloadDir.getAbsolutePath());

        SharedPreferences prefs = getSharedPreferences("mediaflow_prefs", MODE_PRIVATE);
        boolean allowFfmpeg = prefs.getBoolean("allow_ffmpeg", false);
        String ffmpegPath = prefs.getString("ffmpeg_path", "");

        boolean isAudio = audioRadio.isChecked();
        String ext = formatSpinner.getSelectedItem().toString();
        String quality = qualitySpinner.getSelectedItem().toString();
        JSONObject options = new JSONObject();
        try {
            options.put("playlist", playlistCheck.isChecked());
            options.put("subs", subsCheck.isChecked());
            options.put("embed_thumb", thumbCheck.isChecked());
            options.put("sponsor_block", sponsorCheck.isChecked());
            options.put("allow_ffmpeg", allowFfmpeg);
            options.put("ffmpeg_path", ffmpegPath);
            options.put("concurrent", 1);
        } catch (Exception ignored) {
        }

        executor.submit(() -> {
            String raw = backend.callAttr(
                    "download",
                    url,
                    downloadDir.getAbsolutePath(),
                    ext,
                    quality,
                    isAudio,
                    options.toString(),
                    new ProgressBridge()
            ).toString();
            runOnUiThread(() -> handleDownloadResult(raw));
        });
    }

    private void cancelDownload() {
        try {
            backend.callAttr("cancel_current");
        } catch (Exception ignored) {
        }
        setStatus("Cancelling...", false);
        appendLog("Cancel requested");
    }

    private void handleDownloadResult(String raw) {
        setBusy(false, true);
        try {
            JSONObject result = new JSONObject(raw);
            if (!result.optBoolean("ok")) {
                if (result.optBoolean("cancelled")) {
                    progressBar.setProgress(0);
                    setStatus("Cancelled", false);
                    appendLog("CANCELLED");
                } else {
                    setStatus(result.optString("error", "Download failed"), true);
                    appendLog("ERROR  " + result.optString("error"));
                }
                return;
            }
            progressBar.setProgress(1000);
            String title = result.optString("title", "Completed");
            setStatus("Completed in " + String.format("%.1f", result.optDouble("elapsed")) + "s", false);
            appendLog("DONE  " + title);

            JSONArray downloadedFiles = result.optJSONArray("downloaded_files");
            scanDownloadedFiles(downloadedFiles);
        } catch (Exception exc) {
            setStatus("Could not parse download result", true);
            appendLog("ERROR  " + exc.getMessage());
        }
    }

    private void scanDownloadedFiles(JSONArray files) {
        if (files == null || files.length() == 0) return;
        try {
            String[] paths = new String[files.length()];
            for (int i = 0; i < files.length(); i++) {
                paths[i] = files.getString(i);
            }
            android.media.MediaScannerConnection.scanFile(
                    this,
                    paths,
                    null,
                    (path, uri) -> {
                        // Scan completed.
                    }
            );
        } catch (Exception e) {
            appendLog("SCAN ERROR  " + e.getMessage());
        }
    }

    private void loadThumbnail(String urlString) {
        executor.submit(() -> {
            try {
                java.net.URL url = new java.net.URL(urlString);
                java.net.HttpURLConnection connection = (java.net.HttpURLConnection) url.openConnection();
                connection.setDoInput(true);
                connection.connect();
                java.io.InputStream input = connection.getInputStream();
                android.graphics.Bitmap bitmap = android.graphics.BitmapFactory.decodeStream(input);
                runOnUiThread(() -> {
                    if (bitmap != null) {
                        thumbImage.setImageBitmap(bitmap);
                        thumbImage.setVisibility(View.VISIBLE);
                    }
                });
            } catch (Exception e) {
                e.printStackTrace();
            }
        });
    }

    public class ProgressBridge {
        public void onProgress(String raw) {
            runOnUiThread(() -> {
                try {
                    JSONObject progress = new JSONObject(raw);
                    int pct = (int) Math.max(0, Math.min(1000, progress.optDouble("percent", 0) * 1000));
                    progressBar.setProgress(pct);
                    statusText.setText(progress.optString("message", "Working..."));
                    String speed = progress.optString("speed");
                    String eta = progress.optString("eta");
                    speedText.setText(join(listOf(speed, eta), "    "));
                } catch (Exception exc) {
                    statusText.setText("Working...");
                }
            });
        }
    }

    private void updateModeChoices() {
        boolean audio = audioRadio != null && audioRadio.isChecked();
        setSpinnerItems(formatSpinner, audio ? audioFormats : videoFormats);
        setSpinnerItems(qualitySpinner, audio ? audioQualities : videoQualities);
    }

    private void setBusy(boolean busy, boolean downloading) {
        downloadButton.setEnabled(!busy);
        cancelButton.setEnabled(busy && downloading);
    }

    private void setStatus(String message, boolean error) {
        statusText.setText(message);
        statusText.setTextColor(error ? DANGER : TEXT);
    }

    private void appendLog(String line) {
        String old = logText.getText().toString();
        String next = old.isEmpty() ? line : old + "\n" + line;
        logText.setText(next);
    }

    private LinearLayout card() {
        LinearLayout layout = new LinearLayout(this);
        layout.setOrientation(LinearLayout.VERTICAL);
        layout.setPadding(dp(14), dp(14), dp(14), dp(14));
        GradientDrawable bg = new GradientDrawable();
        bg.setColor(CARD);
        bg.setCornerRadius(dp(8));
        bg.setStroke(dp(1), Color.rgb(46, 52, 65));
        layout.setBackground(bg);
        LinearLayout.LayoutParams params = matchWrap();
        params.setMargins(0, 0, 0, dp(12));
        layout.setLayoutParams(params);
        return layout;
    }

    private TextView sectionLabel(String text) {
        TextView view = label(text.toUpperCase(), 12, MUTED, Typeface.BOLD);
        view.setPadding(0, 0, 0, dp(10));
        return view;
    }

    private TextView smallLabel(String text) {
        TextView view = label(text, 13, MUTED, Typeface.BOLD);
        view.setPadding(0, dp(10), 0, dp(4));
        return view;
    }

    private TextView label(String text, int sp, int color, int style) {
        TextView view = new TextView(this);
        view.setText(tr(text));
        view.setTextSize(sp);
        view.setTextColor(color);
        view.setTypeface(Typeface.DEFAULT, style);
        view.setLineSpacing(0, 1.08f);
        view.setGravity(textGravity());
        return view;
    }

    private Button button(String text, int color) {
        Button view = new Button(this);
        view.setText(tr(text));
        view.setTextColor(Color.WHITE);
        view.setTextSize(13);
        view.setAllCaps(false);
        GradientDrawable bg = new GradientDrawable();
        bg.setColor(color);
        bg.setCornerRadius(dp(6));
        view.setBackground(bg);
        return view;
    }

    private RadioButton radio(String text) {
        RadioButton view = new RadioButton(this);
        view.setText(tr(text));
        view.setTextColor(TEXT);
        view.setTextSize(15);
        return view;
    }

    private CheckBox check(String text) {
        CheckBox view = new CheckBox(this);
        view.setText(tr(text));
        view.setTextColor(TEXT);
        view.setTextSize(14);
        view.setGravity(textGravity() | Gravity.CENTER_VERTICAL);
        return view;
    }

    private Spinner spinner() {
        Spinner view = new Spinner(this);
        view.setBackgroundColor(PANEL);
        return view;
    }

    private View space(int width, int height) {
        View view = new View(this);
        view.setLayoutParams(new LinearLayout.LayoutParams(width, height));
        return view;
    }

    private LinearLayout.LayoutParams matchWrap() {
        return new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT
        );
    }

    private void setSpinnerItems(Spinner spinner, List<String> items) {
        ArrayAdapter<String> adapter = new ArrayAdapter<>(
                this,
                android.R.layout.simple_spinner_item,
                items
        );
        adapter.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item);
        spinner.setAdapter(adapter);
    }

    private List<String> jsonList(JSONArray array) throws Exception {
        List<String> result = new ArrayList<>();
        for (int i = 0; i < array.length(); i++) {
            result.add(array.getString(i));
        }
        return result;
    }

    private List<String> listOf(String... values) {
        List<String> result = new ArrayList<>();
        for (String value : values) {
            if (value != null && !value.isEmpty()) {
                result.add(value);
            }
        }
        return result;
    }

    private void addIfPresent(List<String> list, String value) {
        if (value != null && !value.isEmpty()) {
            list.add(value);
        }
    }

    private String join(List<String> items, String separator) {
        StringBuilder builder = new StringBuilder();
        for (String item : items) {
            if (item == null || item.isEmpty()) {
                continue;
            }
            if (builder.length() > 0) {
                builder.append(separator);
            }
            builder.append(item);
        }
        return builder.toString();
    }

    private int dp(int value) {
        return (int) (value * getResources().getDisplayMetrics().density + 0.5f);
    }
}

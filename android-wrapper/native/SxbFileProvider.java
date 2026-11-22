package com.spacexbot.app;

import androidx.core.content.FileProvider;

/** Own FileProvider class so it does not clash with Capacitor's own provider (the manifest needs a different name). */
public class SxbFileProvider extends FileProvider {}

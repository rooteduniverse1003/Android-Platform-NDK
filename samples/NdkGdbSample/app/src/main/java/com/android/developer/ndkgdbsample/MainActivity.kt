package com.android.developer.ndkgdbsample

import android.support.v7.app.AppCompatActivity
import android.os.Bundle
import android.view.View
import android.widget.TextView

class MainActivity : AppCompatActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)
        val tv = findViewById<View>(R.id.hello_textview) as TextView
        tv.text = getHelloString()
    }

    private external fun getHelloString(): String

    companion object {
        init {
            System.loadLibrary("app")
        }
    }
}

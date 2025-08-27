package nethical.digipaws.ui.activity

import android.os.Bundle
import android.text.InputFilter
import android.util.Patterns
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.Button
import android.widget.TextView
import android.widget.Toast
import androidx.activity.OnBackPressedCallback
import androidx.activity.enableEdgeToEdge
import androidx.appcompat.app.AppCompatActivity
import androidx.core.view.ViewCompat
import androidx.core.view.WindowInsetsCompat
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView
import com.google.android.material.dialog.MaterialAlertDialogBuilder
import nethical.digipaws.R
import nethical.digipaws.databinding.ActivityManageKeywordsBinding
import nethical.digipaws.databinding.DialogAddKeywordBinding


class ManageKeywordsActivity : AppCompatActivity() {

    private lateinit var binding: ActivityManageKeywordsBinding
    lateinit var savedKeywordsList: ArrayList<String>
    private lateinit var keywordAdapter: KeywordAdapter
    private var oldSize = 0

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()

        binding = ActivityManageKeywordsBinding.inflate(layoutInflater)
        setContentView(binding.root)

        ViewCompat.setOnApplyWindowInsetsListener(findViewById(R.id.main)) { v, insets ->
            val systemBars = insets.getInsets(WindowInsetsCompat.Type.systemBars())
            v.setPadding(systemBars.left, systemBars.top, systemBars.right, systemBars.bottom)
            insets
        }

        savedKeywordsList = intent.getStringArrayListExtra("PRE_SAVED_KEYWORDS") ?: arrayListOf()
        oldSize = savedKeywordsList.size

        keywordAdapter = KeywordAdapter(savedKeywordsList)
        binding.recyclerView.layoutManager = LinearLayoutManager(this)
        binding.recyclerView.adapter = keywordAdapter

        binding.confirmSelectionKeywords.setOnClickListener {
            val resultIntent = intent.apply {
                putStringArrayListExtra("SELECTED_KEYWORDS", savedKeywordsList)
            }
            setResult(RESULT_OK, resultIntent)
            finish()
        }
        binding.btnAddKeyword.setOnClickListener { makeAddKeywordDialog() }
        onBackPressedDispatcher.addCallback(this, object : OnBackPressedCallback(true) {
            override fun handleOnBackPressed() {
                // Show a confirmation dialog
                if (oldSize != savedKeywordsList.size) {
                    showExitDialog()
                } else {
                    finish()
                }
            }
        })
    }


    private fun showExitDialog() {
        MaterialAlertDialogBuilder(this)
            .setTitle(getString(R.string.discard_changes))
            .setMessage(getString(R.string.are_you_sure_you_want_to_discard_all_changes_and_exit))
            .setPositiveButton(getString(R.string.yes)) { dialog, _ ->
                dialog.dismiss()
                // Allow back press
                finish()
            }
            .setNegativeButton(getString(R.string.cancel)) { dialog, _ ->
                dialog.dismiss()
                // Do nothing, stay on the screen
            }
            .show()
    }
    private fun makeAddKeywordDialog() {
        val dialogBinding = DialogAddKeywordBinding.inflate(layoutInflater)


        val filter = InputFilter { source, _, _, _, _, _ ->
            // Allow Unicode letters and digits (but not special characters or spaces)
            if (source.contains(" ")) {
                "" // Reject the input
            } else {
                source // Accept the input
            }
        }

        // Apply the filter
        dialogBinding.keywordInput.filters = arrayOf(filter)
        MaterialAlertDialogBuilder(this)
            .setTitle(getString(R.string.add_a_new_keyword))
            .setView(dialogBinding.root)
            .setPositiveButton(getString(R.string.add)) { dialog, _ ->
                var keyword = dialogBinding.keywordInput.text.toString().trim()
                if (keyword.isEmpty()) {
                    return@setPositiveButton
                }
                if (Patterns.WEB_URL.matcher(keyword).matches()) {
                    val regex = Regex("^(?:https?://)?(?:www\\.)?([\\w-]+)\\.")
                    keyword = regex.find(keyword)?.groupValues?.get(1) ?: ""
                    Toast.makeText(
                        this,
                        "Cannot add links, converted and added as a word.",
                        Toast.LENGTH_LONG
                    ).show()
                }

                if (savedKeywordsList.contains(keyword)) {
                    Toast.makeText(this, "Same Keyword already exists", Toast.LENGTH_LONG).show()
                    return@setPositiveButton
                }

                savedKeywordsList.add(keyword)
                keywordAdapter.notifyItemInserted(savedKeywordsList.size - 1)

                dialog.dismiss()
            }
            .setNegativeButton(getString(R.string.cancel)) { dialog, _ ->
                dialog.dismiss()
            }
            .show()
    }

    inner class KeywordAdapter(private val keywords: ArrayList<String>) :
        RecyclerView.Adapter<KeywordAdapter.KeywordViewHolder>() {

        inner class KeywordViewHolder(itemView: View) : RecyclerView.ViewHolder(itemView) {
            val keywordTextView: TextView = itemView.findViewById(R.id.keyword_txt)
            val removeBtn: Button = itemView.findViewById(R.id.btn_remove_keyword)
        }

        override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): KeywordViewHolder {
            val view =
                LayoutInflater.from(parent.context).inflate(R.layout.keyword_item, parent, false)
            return KeywordViewHolder(view)
        }

        override fun onBindViewHolder(holder: KeywordViewHolder, position: Int) {
            holder.keywordTextView.text = keywords[position]
            holder.removeBtn.setOnClickListener {
                savedKeywordsList.removeAt(position)
                notifyItemRemoved(position)
            }
        }

        override fun getItemCount(): Int = keywords.size
    }
}

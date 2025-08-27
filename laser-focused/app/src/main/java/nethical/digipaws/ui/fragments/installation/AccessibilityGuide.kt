package nethical.digipaws.ui.fragments.installation

import android.annotation.SuppressLint
import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import androidx.fragment.app.Fragment
import nethical.digipaws.databinding.FragmentAccessibilityGuideBinding

class AccessibilityGuide : Fragment() {
    companion object {
        const val FRAGMENT_ID = "accessibility_guide_fragment"
    }

    private var _binding: FragmentAccessibilityGuideBinding? = null
    private val binding get() = _binding!!  // Safe getter for binding

    override fun onCreateView(
        inflater: LayoutInflater,
        container: ViewGroup?,
        savedInstanceState: Bundle?
    ): View {
        _binding = FragmentAccessibilityGuideBinding.inflate(inflater, container, false)
        return binding.root
    }

    @SuppressLint("CommitPrefEdits")
    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)
        binding.btnNext.setOnClickListener {
            requireActivity().finish()
        }
    }


    override fun onDestroyView() {
        super.onDestroyView()
        _binding = null
    }
}
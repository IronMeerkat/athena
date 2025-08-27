package nethical.digipaws.ui.fragments.installation

import android.content.ActivityNotFoundException
import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.Toast
import androidx.fragment.app.Fragment
import nethical.digipaws.R
import nethical.digipaws.databinding.FragmentWelcomeBinding

class WelcomeFragment : Fragment() {

    companion object {
        const val FRAGMENT_ID = "welcome_fragment"
    }

    private var _binding: FragmentWelcomeBinding? = null
    private val binding get() = _binding!!  // Safe getter for binding

    override fun onCreateView(
        inflater: LayoutInflater,
        container: ViewGroup?,
        savedInstanceState: Bundle?
    ): View {
        _binding = FragmentWelcomeBinding.inflate(inflater, container, false)
        return binding.root
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)

        binding.cbTos.setOnCheckedChangeListener { _, isChecked ->
            binding.btnNext.isEnabled = isChecked
        }
        binding.openTos.setOnClickListener {
            val intent =
                Intent(Intent.ACTION_VIEW, Uri.parse("https://digipaws.life/terms-and-conditions"))
            try {
                startActivity(intent)
            } catch (e: ActivityNotFoundException) {
                Toast.makeText(
                    requireContext(),
                    "No application found to open the link",
                    Toast.LENGTH_SHORT
                ).show()
            }
        }

        binding.btnNext.setOnClickListener {
            requireActivity().supportFragmentManager.beginTransaction()
                .replace(
                    R.id.fragment_holder,
                    PermissionsFragment()
                ) // Replace with FragmentB
                .addToBackStack(null)
                .commit()
        }
    }


    override fun onDestroyView() {
        super.onDestroyView()
        _binding = null
    }
}
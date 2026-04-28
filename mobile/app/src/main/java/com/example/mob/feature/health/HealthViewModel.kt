package com.example.mob.feature.health

import android.app.Activity
import android.content.Context
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.mob.data.repository.HealthRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch

sealed interface HealthSyncState {
    data object Idle : HealthSyncState
    data object Loading : HealthSyncState
    data object Success : HealthSyncState
    data class Error(val message: String) : HealthSyncState
}

class HealthViewModel(context: Context) : ViewModel() {

    private val repository = HealthRepository(context)

    private val _syncState = MutableStateFlow<HealthSyncState>(HealthSyncState.Idle)
    val syncState: StateFlow<HealthSyncState> = _syncState

    val permissionKeys = repository.permissionKeys

    fun hasAllPermissions(): Boolean = repository.hasAllPermissions()

    // Samsung Health 권한 요청 (connect() 후 호출해야 함)
    fun requestPermissions(activity: Activity) {
        viewModelScope.launch {
            repository.connect()
            repository.requestPermissions(activity)
        }
    }

    fun syncWatchData() {
        viewModelScope.launch {
            _syncState.value = HealthSyncState.Loading
            _syncState.value = repository.syncToServer().fold(
                onSuccess = { HealthSyncState.Success },
                onFailure = { HealthSyncState.Error(it.message ?: "알 수 없는 오류") }
            )
        }
    }
}
